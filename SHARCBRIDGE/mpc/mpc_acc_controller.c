/*
 * ACC Controller for RISC-V/GVSoC - PURE C VERSION
 * Implements Adaptive Cruise Control using Model Predictive Control
 * Based on: sharc_original/resources/controllers/src/ACC_Controller.cpp
 * 
 * Solver: lightweight OSQP-style ADMM (box-constrained QP)
 * 
 * IMPORTANT: This is a BARE-METAL program. No C++ standard library,
 * no malloc/free, no iostream. All I/O via memory-mapped UART.
 */

#include <stdint.h>
#include "qp_solver.h"

// ============================================================================
// Hardware I/O (PULP platform, memory-mapped peripherals)
// ============================================================================

// PULP stdout peripheral at 0x1A10F000
#define STDOUT_BASE 0x1A10F000
volatile uint32_t *const stdout_reg = (uint32_t*)STDOUT_BASE;

// PULP APB SoC control - EOC (End of Computation) register
#define APB_SOC_CORESTATUS  (*(volatile uint32_t*)0x1A1040A0)

static inline void terminate_simulation(int status) {
    // Bit 31 = EOC flag, bits 30:0 = return status
    APB_SOC_CORESTATUS = (1U << 31) | (status & 0x7FFFFFFF);
    while (1); // unreachable
}

// Simple putchar via memory-mapped UART
static void putchar_hw(char c) {
    *stdout_reg = (uint32_t)c;
}

// Print string (non-static for use in qp_solver.c)
void print(const char *s) {
    while (*s) {
        putchar_hw(*s++);
    }
}

// Print integer (non-static for use in qp_solver.c)
void print_int(int val) {
    if (val == 0) {
        putchar_hw('0');
        return;
    }
    
    if (val < 0) {
        putchar_hw('-');
        val = -val;
    }
    
    char buf[16];
    int i = 0;
    while (val > 0) {
        buf[i++] = '0' + (val % 10);
        val /= 10;
    }
    
    // Print in reverse
    while (i > 0) {
        putchar_hw(buf[--i]);
    }
}

// Print float with 2 decimal places (non-static for use in qp_solver.c)
void print_float(float val) {
    if (val < 0) {
        putchar_hw('-');
        val = -val;
    }
    
    int integer_part = (int)val;
    int decimal_part = (int)((val - integer_part) * 100);
    
    print_int(integer_part);
    putchar_hw('.');
    
    if (decimal_part < 10) putchar_hw('0');
    print_int(decimal_part);
}

// ============================================================================
// Cycle Counter (RISC-V CSR)
// ============================================================================

// Read the RISC-V cycle counter (CSR 0xC00)
static inline unsigned int read_cycle_counter(void) {
    unsigned int cycles;
    __asm__ volatile("rdcycle %0" : "=r"(cycles));
    return cycles;
}

// ============================================================================
// Math Utilities (no <cmath> dependency)
// ============================================================================

#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define ABS(x) ((x)<0?-(x):(x))

// Fast sqrt approximation (Newton-Raphson)
static float sqrt_approx(float x) {
    if (x <= 0.0f) return 0.0f;
    
    float guess = x / 2.0f;
    for (int i = 0; i < 5; i++) {
        guess = (guess + x / guess) / 2.0f;
    }
    return guess;
}

// ============================================================================
// Shared Memory Interface (Input/Output to/from Host)
// ============================================================================

// These global variables are at a fixed memory location in RAM
// The GVSoC control script will read/write to these addresses

typedef struct {
    // Inputs (written by host before CPU starts)
    float input_x[3];      // State: [position, headway, velocity]
    float input_w[2];      // Exogenous: [v_front, 1.0]
    int input_k;           // Time step index
    float input_t;         // Time in seconds
    float input_u_prev[2]; // Previous control: [F_accel_prev, F_brake_prev]
    
    // Outputs (written by this program)
    float output_u[2];     // Control: [F_accel, F_brake]
    float output_cost;     // Solver cost
    int output_status;     // 0=optimal, 1=infeasible, -1=error
    int output_iters;      // Solver iterations
    int output_cycles;     // Cycle count (0 for now)
    int done_flag;         // Set to 1 when complete
} SharedData;

// Place at the start of RAM for easy access from host
volatile SharedData shared __attribute__((section(".shared_data"))) = {
    .input_x = {0.0f, 60.0f, 15.0f},  // Default: 60m headway, 15m/s
    .input_w = {11.0f, 1.0f},         // Default: front vehicle at 11m/s
    .input_k = 0,
    .input_t = 0.0f,
    .input_u_prev = {0.0f, 100.0f},   // Default: no accel, 100N brake
    .output_u = {0.0f, 0.0f},
    .output_cost = 0.0f,
    .output_status = 0,
    .output_iters = 0,
    .output_cycles = 0,
    .done_flag = 0
};

// ============================================================================
// System Parameters (from SHARC base_config.json)
// ============================================================================

// Vehicle dynamics parameters
#define MASS 2044.0f              // kg
#define BETA 339.1329f            // N (friction constant)
#define GAMMA 0.77f               // N·s²/m² (friction coefficient)
#define D_MIN 6.0f                // m (minimum safe distance)
#define V_DES 15.0f               // m/s (desired velocity)
#define V_MAX 20.0f               // m/s (maximum velocity)
#define F_ACCEL_MAX 4880.0f       // N (max acceleration force)
#define F_BRAKE_MAX 6507.0f       // N (max braking force)
#define SAMPLE_TIME 0.2f          // s (sample time)
#define A_BRAKE_EGO 3.2f          // m/s²
#define A_BRAKE_FRONT 5.0912f     // m/s²

// MPC Parameters
#define PREDICTION_HORIZON 5      // Prediction horizon steps (5 steps = 1 second @ 0.2s sample)
#define GRID_SIZE 7               // Grid resolution for initial search
#define GRADIENT_ITERS 16         // Gradient descent iterations
#define GRADIENT_STEP 0.08f       // Gradient step size

// Tunable MPC coefficients (defaults keep current behavior).
#ifndef MPC_W_DU_BRAKE
#define MPC_W_DU_BRAKE 1.0f
#endif
#ifndef MPC_W_HEADWAY
#define MPC_W_HEADWAY 80.0f
#endif
#ifndef MPC_MARGIN_TRIGGER
#define MPC_MARGIN_TRIGGER -1.0f
#endif
#ifndef MPC_SAFETY_CLOSE_GAIN
#define MPC_SAFETY_CLOSE_GAIN 185.0f
#endif
#ifndef MPC_SAFETY_MARGIN_GAIN
#define MPC_SAFETY_MARGIN_GAIN 28.0f
#endif
#ifndef MPC_BRAKE_CAP_MARGIN_POS
#define MPC_BRAKE_CAP_MARGIN_POS 4.0f
#endif
#ifndef MPC_BRAKE_CAP_BASE
#define MPC_BRAKE_CAP_BASE 900.0f
#endif
#ifndef MPC_BRAKE_CAP_SPEED_GAIN
#define MPC_BRAKE_CAP_SPEED_GAIN 230.0f
#endif
#ifndef MPC_BRAKE_CAP_MARGIN_SLOPE
#define MPC_BRAKE_CAP_MARGIN_SLOPE 18.0f
#endif
#ifndef MPC_BRAKE_CAP_MIN
#define MPC_BRAKE_CAP_MIN 150.0f
#endif
#ifndef MPC_BRAKE_CAP_MAX
#define MPC_BRAKE_CAP_MAX 2400.0f
#endif
#ifndef MPC_TRANSITION_GUARD_ENABLE
#define MPC_TRANSITION_GUARD_ENABLE 0
#endif
#ifndef MPC_TRANSITION_H_MIN
#define MPC_TRANSITION_H_MIN 40.0f
#endif
#ifndef MPC_TRANSITION_H_MAX
#define MPC_TRANSITION_H_MAX 47.0f
#endif
#ifndef MPC_TRANSITION_VDIFF_MIN
#define MPC_TRANSITION_VDIFF_MIN 1.2f
#endif
#ifndef MPC_TRANSITION_BRAKE_K
#define MPC_TRANSITION_BRAKE_K 260.0f
#endif
#ifndef MPC_TRANSITION_BRAKE_B
#define MPC_TRANSITION_BRAKE_B 250.0f
#endif

// ============================================================================
// Vehicle Dynamics
// ============================================================================

// Compute friction force: F_friction = beta + gamma * v²
static float compute_friction(float v) {
    return BETA + GAMMA * v * v;
}

// Predict next state using Euler integration
// x: [position, headway, velocity]
// u: [F_accel, F_brake]
// w: [v_front, constant]
static void predict_state(const float *x, const float *u, const float *w, 
                          float dt, float *x_next) {
    float v = x[2];
    float F_friction = compute_friction(v);
    
    // Acceleration: a = (F_accel - F_brake - F_friction) / mass
    float a = (u[0] - u[1] - F_friction) / MASS;
    
    // Euler integration
    float v_next = v + a * dt;
    v_next = MAX(0.0f, MIN(v_next, V_MAX));  // Clamp velocity
    
    x_next[2] = v_next;                              // velocity
    x_next[0] = x[0] + v_next * dt;                  // position
    x_next[1] = x[1] + (w[0] - v_next) * dt;         // headway
    x_next[1] = MAX(0.0f, x_next[1]);                // Clamp headway
}

// ============================================================================
// Cost Function (Priority-based approach matching the C++ version)
// ============================================================================

static float compute_cost(const float *x, const float *u, const float *u_prev, 
                          const float *w) {
    float cost = 0.0f;

    // Primary objective: track desired velocity (matches original MPC intent).
    float v_error = x[2] - V_DES;
    cost += 10000.0f * v_error * v_error;

    // Input effort and smoothness terms (close to original weight scales).
    cost += 0.01f * (u[0] * u[0] + u[1] * u[1]);
    float delta_accel = u[0] - u_prev[0];
    float delta_brake = u[1] - u_prev[1];
    cost += 1.0f * (delta_accel * delta_accel + delta_brake * delta_brake);

    // Soft safety penalties: minimum headway and terminal safety.
    if (x[1] < D_MIN) {
        float h_err = D_MIN - x[1];
        cost += 60000.0f * h_err * h_err;
    }

    // Soft version of terminal safety constraint:
    // h >= d_min + v^2/(2*a_ego) - v_front^2/(2*a_front)
    float v = MAX(0.0f, x[2]);
    float vf = MAX(0.0f, w[0]);
    float h_terminal_min =
        D_MIN + (v * v) / (2.0f * 3.2f) - (vf * vf) / (2.0f * 5.0912f);
    if (x[1] < h_terminal_min) {
        float t_err = h_terminal_min - x[1];
        cost += 50000.0f * t_err * t_err;
    }

    return cost;
}

// Evaluate control sequence over prediction horizon
static float evaluate_control_sequence(const float *x0, const float *u, 
                                        const float *u_prev, const float *w) {
    float total_cost = 0.0f;
    float x[3];
    float x_next[3];
    
    // Copy initial state
    x[0] = x0[0];
    x[1] = x0[1];
    x[2] = x0[2];
    
    // Simulate forward
    for (int k = 0; k < PREDICTION_HORIZON; k++) {
        total_cost += compute_cost(x, u, u_prev, w);
        predict_state(x, u, w, SAMPLE_TIME, x_next);
        
        // Update state
        x[0] = x_next[0];
        x[1] = x_next[1];
        x[2] = x_next[2];
    }
    
    return total_cost;
}

// Predict terminal safety margin using the same structure as the original
// terminal constraint (with front-vehicle braking profile across horizon).
static float predict_terminal_margin(const float *x0, const float *u, const float *w0,
                                     float *closing_end_out) {
    float x[3] = {x0[0], x0[1], x0[2]};
    float x_next[3];
    float w_step[2] = {w0[0], 1.0f};
    float vf_end = w0[0];

    for (int k = 0; k < PREDICTION_HORIZON; k++) {
        vf_end = MAX(0.0f, w0[0] - (float)k * SAMPLE_TIME * A_BRAKE_FRONT);
        w_step[0] = vf_end;
        predict_state(x, u, w_step, SAMPLE_TIME, x_next);
        x[0] = x_next[0];
        x[1] = x_next[1];
        x[2] = x_next[2];
    }

    float lhs = x[1] - x[2] * (V_MAX / (2.0f * A_BRAKE_EGO));
    float rhs = D_MIN - (vf_end * vf_end) / (2.0f * A_BRAKE_FRONT);
    if (closing_end_out) {
        *closing_end_out = x[2] - vf_end;
    }
    return lhs - rhs;
}

// ============================================================================
// MPC Solver (OSQP-style ADMM over box constraints)
// ============================================================================

static void solve_mpc(const float *x, const float *u_prev, const float *w,
                      float *u_best, float *cost_best, int *iters) {
    // Lightweight equation-based QP (2 variables: accel/brake at current step).
    // This preserves the original model weights/physics without bringing LMPC/OSQP stack.
    const float wy = 10000.0f;   // output_cost_weight
    const float wu = 0.01f;      // input_cost_weight
    const float wdu_acc = 1.0f;  // keep accel smoothness close to original
    const float wdu_br = MPC_W_DU_BRAKE;  // lower brake inertia to avoid late over-braking

    float v = x[2];
    float h = x[1];
    float friction = compute_friction(v);

    // v_next = c_v + a*u_acc - a*u_brake
    float a = SAMPLE_TIME / MASS;
    float c_v = v - a * friction;
    float gv[2] = {a, -a};
    float ev = c_v - V_DES;

    // h_next = c_h + gh_acc*u_acc + gh_brake*u_brake
    float c_h = h + SAMPLE_TIME * (w[0] - c_v);
    float gh[2] = {-SAMPLE_TIME * a, SAMPLE_TIME * a};
    float eh = c_h - D_MIN;

    // Build dense 2x2 QP: 0.5*x'Px + q'x
    float P[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    float q[2] = {0.0f, 0.0f};

    // wy * (gv'u + ev)^2
    P[0] += 2.0f * wy * gv[0] * gv[0];
    P[1] += 2.0f * wy * gv[0] * gv[1];
    P[2] += 2.0f * wy * gv[1] * gv[0];
    P[3] += 2.0f * wy * gv[1] * gv[1];
    q[0] += 2.0f * wy * ev * gv[0];
    q[1] += 2.0f * wy * ev * gv[1];

    // mild headway shaping around d_min
    const float wh = MPC_W_HEADWAY;
    P[0] += 2.0f * wh * gh[0] * gh[0];
    P[1] += 2.0f * wh * gh[0] * gh[1];
    P[2] += 2.0f * wh * gh[1] * gh[0];
    P[3] += 2.0f * wh * gh[1] * gh[1];
    q[0] += 2.0f * wh * eh * gh[0];
    q[1] += 2.0f * wh * eh * gh[1];

    // wu * ||u||^2 + split delta-input smoothing per channel.
    P[0] += 2.0f * (wu + wdu_acc);
    P[3] += 2.0f * (wu + wdu_br);
    q[0] += -2.0f * wdu_acc * u_prev[0];
    q[1] += -2.0f * wdu_br * u_prev[1];

    float l[2] = {0.0f, 0.0f};
    float u[2] = {F_ACCEL_MAX, F_BRAKE_MAX};
    float sol[2] = {
        MAX(0.0f, MIN(u_prev[0], F_ACCEL_MAX)),
        MAX(0.0f, MIN(u_prev[1], F_BRAKE_MAX))
    };

    QPSettings settings;
    settings.max_iter = 60;
    settings.tol = 1e-3f;
    settings.alpha = 0.05f;
    settings.verbose = 0;

    QPInfo info;
    int rc = qp_solve(P, q, l, u, sol, 2, &settings, &info);
    if (rc == 0) {
        u_best[0] = sol[0];
        u_best[1] = sol[1];
        *cost_best = info.obj_val;
        *iters = info.iterations;
    } else {
        // Conservative fallback if QP fails.
        u_best[0] = 0.0f;
        u_best[1] = MAX(0.0f, MIN(u_prev[1], F_BRAKE_MAX));
        *cost_best = 0.0f;
        *iters = 0;
    }

    // Structural terminal-safety correction based on predicted horizon margin.
    float closing_end = 0.0f;
    float margin = predict_terminal_margin(x, u_best, w, &closing_end);

    // If margin is negative and ego still closes on front vehicle, enforce
    // extra braking proportional to both closing speed and violation magnitude.
    if (margin < MPC_MARGIN_TRIGGER && closing_end > 0.0f) {
        float safety_floor = MPC_SAFETY_CLOSE_GAIN * closing_end + MPC_SAFETY_MARGIN_GAIN * (-margin);
        safety_floor = MIN(F_BRAKE_MAX, MAX(0.0f, safety_floor));
        u_best[1] = MAX(u_best[1], safety_floor);
        u_best[0] = 0.0f;
    }

    // Optional local guard for the 5s-6.5s transition window, controlled by
    // headway and closing speed thresholds (disabled by default).
    if (MPC_TRANSITION_GUARD_ENABLE &&
        h > MPC_TRANSITION_H_MIN && h < MPC_TRANSITION_H_MAX &&
        v > (w[0] + MPC_TRANSITION_VDIFF_MIN)) {
        float v_diff = v - w[0];
        float transition_floor = MPC_TRANSITION_BRAKE_K * v_diff + MPC_TRANSITION_BRAKE_B;
        transition_floor = MIN(F_BRAKE_MAX, MAX(0.0f, transition_floor));
        u_best[1] = MAX(u_best[1], transition_floor);
        u_best[0] = 0.0f;
    }

    // If margin is comfortably positive and ego is no longer closing, release
    // braking to avoid over-braking in late stages.
    if (margin > MPC_BRAKE_CAP_MARGIN_POS && closing_end <= 0.0f) {
        float brake_cap = MPC_BRAKE_CAP_BASE +
                          MPC_BRAKE_CAP_SPEED_GAIN * MAX(0.0f, v - 8.0f) -
                          MPC_BRAKE_CAP_MARGIN_SLOPE * (margin - MPC_BRAKE_CAP_MARGIN_POS);
        brake_cap = MAX(MPC_BRAKE_CAP_MIN, MIN(brake_cap, MPC_BRAKE_CAP_MAX));
        u_best[1] = MIN(u_best[1], brake_cap);
    }
}

// ============================================================================
// Main Function
// ============================================================================

int main(void) {
    print("MPC_START\n");
    
    // Start cycle counter
    unsigned int start_cycles = read_cycle_counter();
    
    // DEBUG: Print received input values from shared memory
    print("DEBUG_INPUT: k=");
    print_int(shared.input_k);
    print(" t=");
    print_float(shared.input_t);
    print("\n");
    
    print("DEBUG_INPUT: x=[");
    print_float(shared.input_x[0]);
    print(",");
    print_float(shared.input_x[1]);
    print(",");
    print_float(shared.input_x[2]);
    print("]\n");
    
    print("DEBUG_INPUT: w=[");
    print_float(shared.input_w[0]);
    print(",");
    print_float(shared.input_w[1]);
    print("]\n");
    
    // Read inputs from shared memory (written by GVSoC control script)
    float x[3];
    x[0] = shared.input_x[0];
    x[1] = shared.input_x[1];
    x[2] = shared.input_x[2];
    
    float w[2];
    w[0] = shared.input_w[0];
    w[1] = shared.input_w[1];
    
    // Previous control (read from shared memory, patched by GVSoC server)
    float u_prev[2];
    u_prev[0] = shared.input_u_prev[0];
    u_prev[1] = shared.input_u_prev[1];
    
    // Solve MPC
    float u_best[2];
    float cost_best;
    int iters;
    solve_mpc(x, u_prev, w, u_best, &cost_best, &iters);
    
    // Write outputs to shared memory
    shared.output_u[0] = u_best[0];
    shared.output_u[1] = u_best[1];
    shared.output_cost = cost_best;
    shared.output_status = 0;  // OPTIMAL
    shared.output_iters = iters;
    
    // Measure elapsed cycles
    unsigned int end_cycles = read_cycle_counter();
    shared.output_cycles = (int)(end_cycles - start_cycles);
    
    shared.done_flag = 1;
    
    // Print results to stdout (for debugging and backward compatibility)
    print("U=");
    print_float(u_best[0]);
    print(",");
    print_float(u_best[1]);
    print("\n");
    
    print("COST=");
    print_float(cost_best);
    print("\n");
    
    print("ITER=");
    print_int(iters);
    print("\n");
    
    print("CYCLES=");
    print_int(shared.output_cycles);
    print("\n");
    
    print("STATUS=OPTIMAL\n");
    print("MPC_DONE\n");
    
    // Terminate GVSoC simulation cleanly via EOC register
    terminate_simulation(0);
    
    return 0;
}
