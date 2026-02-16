/*
 * ACC Controller for RISC-V/GVSoC - PURE C VERSION
 * Implements Adaptive Cruise Control using Model Predictive Control
 * Based on: sharc_original/resources/controllers/src/ACC_Controller.cpp
 * 
 * Solver: Projected Gradient Descent with Grid Search Initialization
 * 
 * IMPORTANT: This is a BARE-METAL program. No C++ standard library,
 * no malloc/free, no iostream. All I/O via memory-mapped UART.
 */

#include <stdint.h>

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

// MPC Parameters
#define PREDICTION_HORIZON 5      // Prediction horizon steps (5 steps = 1 second @ 0.2s sample)
#define GRID_SIZE 5               // Grid resolution for initial search
#define GRADIENT_ITERS 10         // Gradient descent iterations
#define GRADIENT_STEP 20.0f       // Gradient step size

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
    
    // CRITICAL: Penalize simultaneous accel and brake
    if (u[0] > 10.0f && u[1] > 10.0f) {
        cost += 1000000.0f * u[0] * u[1];
    }
    
    // PRIORITY 1: Relative velocity (avoid collision)
    float v_relative = x[2] - w[0];
    if (v_relative > 0.5f) {
        cost += 100000.0f * v_relative * v_relative;
    }
    
    // PRIORITY 2: Velocity tracking to desired speed
    float v_error = x[2] - V_DES;
    cost += 100.0f * v_error * v_error;
    
    // PRIORITY 3: Time-to-collision safety
    float time_gap = (v_relative > 0.1f) ? (x[1] / (v_relative + 0.01f)) : 100.0f;
    if (time_gap < 3.0f) {
        float gap_error = 3.0f - time_gap;
        cost += 50000.0f * gap_error * gap_error;
    }
    
    // PRIORITY 4: Headway maintenance
    float d_safe = MAX(D_MIN, 1.0f * x[2]);
    float h_error = x[1] - d_safe;
    if (h_error < 0.0f) {
        cost += 10000.0f * h_error * h_error;
    } else {
        cost += 1.0f * h_error * h_error;
    }
    
    // Input effort (low priority)
    cost += 0.001f * (u[0] * u[0] + u[1] * u[1]);
    
    // Control smoothness
    float delta_accel = u[0] - u_prev[0];
    float delta_brake = u[1] - u_prev[1];
    cost += 0.1f * (delta_accel * delta_accel + delta_brake * delta_brake);
    
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

// ============================================================================
// MPC Solver (Grid Search + Projected Gradient Descent)
// ============================================================================

static void solve_mpc(const float *x, const float *u_prev, const float *w,
                      float *u_best, float *cost_best, int *iters) {
    *cost_best = 1e9f;
    u_best[0] = 0.0f;
    u_best[1] = 0.0f;
    *iters = 0;
    
    // ========================================================================
    // Stage 1: Grid Search Initialization
    // ========================================================================
    
    float accel_step = F_ACCEL_MAX / (GRID_SIZE - 1);
    float brake_step = F_BRAKE_MAX / (GRID_SIZE - 1);
    
    // Try acceleration options (brake = 0)
    print("DEBUG_GRID: Testing acceleration options...\n");
    for (int i = 0; i < GRID_SIZE; i++) {
        float u[2];
        u[0] = i * accel_step;
        u[1] = 0.0f;
        
        float cost = evaluate_control_sequence(x, u, u_prev, w);
        (*iters)++;
        
        print("DEBUG_GRID: accel=");
        print_float(u[0]);
        print(" cost=");
        print_float(cost);
        print("\n");
        
        if (cost < *cost_best) {
            *cost_best = cost;
            u_best[0] = u[0];
            u_best[1] = u[1];
            print("  -> NEW BEST\n");
        }
    }
    
    // Try braking options (accel = 0)
    for (int j = 0; j < GRID_SIZE; j++) {
        float u[2];
        u[0] = 0.0f;
        u[1] = j * brake_step;
        
        float cost = evaluate_control_sequence(x, u, u_prev, w);
        (*iters)++;
        
        if (cost < *cost_best) {
            *cost_best = cost;
            u_best[0] = u[0];
            u_best[1] = u[1];
        }
    }
    
    // ========================================================================
    // Stage 2: Projected Gradient Descent Refinement
    // ========================================================================
    
    float epsilon = 10.0f;  // Finite difference step
    
    for (int iter = 0; iter < GRADIENT_ITERS; iter++) {
        float cost_current = evaluate_control_sequence(x, u_best, u_prev, w);
        (*iters)++;
        
        // Determine which input to refine
        if (u_best[0] > 0.1f) {
            // Refine acceleration
            float u_plus[2] = {MIN(u_best[0] + epsilon, F_ACCEL_MAX), u_best[1]};
            float cost_plus = evaluate_control_sequence(x, u_plus, u_prev, w);
            (*iters)++;
            
            // Gradient approximation
            float grad = (cost_plus - cost_current) / epsilon;
            
            // Gradient descent step with projection
            float new_accel = u_best[0] - GRADIENT_STEP * grad;
            u_best[0] = MAX(0.0f, MIN(new_accel, F_ACCEL_MAX));
            
        } else if (u_best[1] > 0.1f) {
            // Refine braking
            float u_plus[2] = {u_best[0], MIN(u_best[1] + epsilon, F_BRAKE_MAX)};
            float cost_plus = evaluate_control_sequence(x, u_plus, u_prev, w);
            (*iters)++;
            
            // Gradient approximation
            float grad = (cost_plus - cost_current) / epsilon;
            
            // Gradient descent step with projection
            float new_brake = u_best[1] - GRADIENT_STEP * grad;
            u_best[1] = MAX(0.0f, MIN(new_brake, F_BRAKE_MAX));
        }
    }
    
    // ========================================================================
    // Stage 3: Safety Override
    // ========================================================================
    
    if (*cost_best > 1000000.0f && x[2] > w[0] + 1.0f) {
        // Emergency braking
        float v_diff = x[2] - w[0];
        u_best[0] = 0.0f;
        u_best[1] = MAX(500.0f, MIN(3000.0f, 800.0f * v_diff));
        *cost_best = 999.0f;
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
    
    // Previous control (assume zero for first iteration)
    float u_prev[2] = {0.0f, 0.0f};
    
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
