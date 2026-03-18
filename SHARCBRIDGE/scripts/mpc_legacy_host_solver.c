#include <math.h>
#include <stddef.h>

#define MASS 2044.0f
#define BETA 339.1329f
#define GAMMA 0.77f
#define D_MIN 6.0f
#define V_DES 15.0f
#define V_MAX 20.0f
#define F_ACCEL_MAX 4880.0f
#define F_BRAKE_MAX 6507.0f
#define SAMPLE_TIME 0.2f
#define A_BRAKE_EGO 3.2f
#define A_BRAKE_FRONT 5.0912f
#define PREDICTION_HORIZON 5

#define MPC_W_DU_BRAKE 1.0f
#define MPC_W_HEADWAY 80.0f
#define MPC_MARGIN_TRIGGER -1.0f
#define MPC_SAFETY_CLOSE_GAIN 185.0f
#define MPC_SAFETY_MARGIN_GAIN 28.0f
#define MPC_BRAKE_CAP_MARGIN_POS 4.0f
#define MPC_BRAKE_CAP_BASE 900.0f
#define MPC_BRAKE_CAP_SPEED_GAIN 230.0f
#define MPC_BRAKE_CAP_MARGIN_SLOPE 18.0f
#define MPC_BRAKE_CAP_MIN 150.0f
#define MPC_BRAKE_CAP_MAX 2400.0f
#define MPC_TRANSITION_GUARD_ENABLE 0
#define MPC_TRANSITION_H_MIN 40.0f
#define MPC_TRANSITION_H_MAX 47.0f
#define MPC_TRANSITION_VDIFF_MIN 1.2f
#define MPC_TRANSITION_BRAKE_K 260.0f
#define MPC_TRANSITION_BRAKE_B 250.0f

#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))

typedef struct {
    int max_iter;
    float tol;
    float alpha;
} QPSettings;

typedef struct {
    float obj_val;
    int iterations;
    int converged;
} QPInfo;

static float compute_friction(float v) {
    return BETA + GAMMA * v * v;
}

static void predict_state(const float *x, const float *u, const float *w, float dt, float *x_next) {
    float v = x[2];
    float F_friction = compute_friction(v);
    float a = (u[0] - u[1] - F_friction) / MASS;
    float v_next = v + a * dt;
    v_next = MAX(0.0f, MIN(v_next, V_MAX));

    x_next[2] = v_next;
    x_next[0] = x[0] + v_next * dt;
    x_next[1] = x[1] + (w[0] - v_next) * dt;
    x_next[1] = MAX(0.0f, x_next[1]);
}

static float predict_terminal_margin(const float *x0, const float *u, const float *w0, float *closing_end_out) {
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

static int assemble_acc_qp(const float *x, const float *u_prev, const float *w,
                           float *P, float *q, float *l, float *u) {
    const float wy = 10000.0f;
    const float wu = 0.01f;
    const float wdu_acc = 1.0f;
    const float wdu_br = MPC_W_DU_BRAKE;
    const float wh = MPC_W_HEADWAY;

    if (x == NULL || u_prev == NULL || w == NULL || P == NULL || q == NULL || l == NULL || u == NULL) {
        return -10;
    }

    float v = x[2];
    float h = x[1];
    float friction = compute_friction(v);

    float a = SAMPLE_TIME / MASS;
    float c_v = v - a * friction;
    float gv[2] = {a, -a};
    float ev = c_v - V_DES;

    float c_h = h + SAMPLE_TIME * (w[0] - c_v);
    float gh[2] = {-SAMPLE_TIME * a, SAMPLE_TIME * a};
    float eh = c_h - D_MIN;

    P[0] = 0.0f;
    P[1] = 0.0f;
    P[2] = 0.0f;
    P[3] = 0.0f;
    q[0] = 0.0f;
    q[1] = 0.0f;

    P[0] += 2.0f * wy * gv[0] * gv[0];
    P[1] += 2.0f * wy * gv[0] * gv[1];
    P[2] += 2.0f * wy * gv[1] * gv[0];
    P[3] += 2.0f * wy * gv[1] * gv[1];
    q[0] += 2.0f * wy * ev * gv[0];
    q[1] += 2.0f * wy * ev * gv[1];

    P[0] += 2.0f * wh * gh[0] * gh[0];
    P[1] += 2.0f * wh * gh[0] * gh[1];
    P[2] += 2.0f * wh * gh[1] * gh[0];
    P[3] += 2.0f * wh * gh[1] * gh[1];
    q[0] += 2.0f * wh * eh * gh[0];
    q[1] += 2.0f * wh * eh * gh[1];

    P[0] += 2.0f * (wu + wdu_acc);
    P[3] += 2.0f * (wu + wdu_br);
    q[0] += -2.0f * wdu_acc * u_prev[0];
    q[1] += -2.0f * wdu_br * u_prev[1];

    l[0] = 0.0f;
    l[1] = 0.0f;
    u[0] = F_ACCEL_MAX;
    u[1] = F_BRAKE_MAX;
    return 0;
}

static void project_box(float *x, const float *l, const float *u, int n) {
    for (int i = 0; i < n; i++) {
        if (x[i] < l[i]) x[i] = l[i];
        if (x[i] > u[i]) x[i] = u[i];
    }
}

static float compute_objective(const float *P, const float *q, const float *x, int n) {
    float obj = 0.0f;

    for (int i = 0; i < n; i++) {
        obj += q[i] * x[i];
    }

    for (int i = 0; i < n; i++) {
        float Px_i = 0.0f;
        for (int j = 0; j < n; j++) {
            Px_i += P[i * n + j] * x[j];
        }
        obj += 0.5f * x[i] * Px_i;
    }

    return obj;
}

// Cholesky factorization (A = L*L^T), row-major.
static int cholesky_decompose(const float *A, float *L, int n) {
    for (int i = 0; i < n * n; i++) {
        L[i] = 0.0f;
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j <= i; j++) {
            float sum = A[i * n + j];
            for (int k = 0; k < j; k++) {
                sum -= L[i * n + k] * L[j * n + k];
            }

            if (i == j) {
                if (sum <= 1e-12f) {
                    return -1;
                }
                L[i * n + j] = sqrtf(sum);
            } else {
                L[i * n + j] = sum / L[j * n + j];
            }
        }
    }
    return 0;
}

static void cholesky_solve(const float *L, const float *b, float *x, int n) {
    float y[20] = {0};

    for (int i = 0; i < n; i++) {
        float sum = b[i];
        for (int j = 0; j < i; j++) {
            sum -= L[i * n + j] * y[j];
        }
        y[i] = sum / L[i * n + i];
    }

    for (int i = n - 1; i >= 0; i--) {
        float sum = y[i];
        for (int j = i + 1; j < n; j++) {
            sum -= L[j * n + i] * x[j];
        }
        x[i] = sum / L[i * n + i];
    }
}

static int qp_solve(const float *P, const float *q, const float *l, const float *u,
                    float *x, int n, const QPSettings *settings, QPInfo *info) {
    float K[20 * 20] = {0};
    float L[20 * 20] = {0};
    float rhs[20] = {0};
    float z[20] = {0};
    float z_prev[20] = {0};
    float y[20] = {0};

    if (n <= 0 || n > 20) {
        return -1;
    }

    const int max_iter = settings->max_iter > 0 ? settings->max_iter : 60;
    const float tol = settings->tol > 0.0f ? settings->tol : 1e-3f;
    float rho = settings->alpha > 0.0f ? settings->alpha : 0.05f;
    if (rho < 1e-6f) {
        rho = 1e-6f;
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            K[i * n + j] = P[i * n + j];
        }
        K[i * n + i] += rho;
    }

    if (cholesky_decompose(K, L, n) != 0) {
        return -2;
    }

    project_box(x, l, u, n);
    for (int i = 0; i < n; i++) {
        z[i] = x[i];
        y[i] = 0.0f;
    }

    for (int iter = 0; iter < max_iter; iter++) {
        for (int i = 0; i < n; i++) {
            rhs[i] = rho * (z[i] - y[i]) - q[i];
        }
        cholesky_solve(L, rhs, x, n);

        float r_norm_sq = 0.0f;
        float s_norm_sq = 0.0f;
        for (int i = 0; i < n; i++) {
            z_prev[i] = z[i];
            z[i] = x[i] + y[i];
            if (z[i] < l[i]) z[i] = l[i];
            if (z[i] > u[i]) z[i] = u[i];
            y[i] += x[i] - z[i];

            {
                float r_i = x[i] - z[i];
                float s_i = rho * (z[i] - z_prev[i]);
                r_norm_sq += r_i * r_i;
                s_norm_sq += s_i * s_i;
            }
        }

        if (r_norm_sq <= tol * tol && s_norm_sq <= tol * tol) {
            for (int i = 0; i < n; i++) {
                x[i] = z[i];
            }
            info->obj_val = compute_objective(P, q, x, n);
            info->iterations = iter + 1;
            info->converged = 1;
            return 0;
        }
    }

    for (int i = 0; i < n; i++) {
        x[i] = z[i];
    }
    info->obj_val = compute_objective(P, q, x, n);
    info->iterations = max_iter;
    info->converged = 0;
    return 0;
}

int build_acc_qp_matrices(const float *x, const float *u_prev, const float *w,
                          float *P_out, float *q_out, float *l_out, float *u_out) {
    return assemble_acc_qp(x, u_prev, w, P_out, q_out, l_out, u_out);
}

int solve_mpc_step(const float *x, const float *u_prev, const float *w,
                   float *u_out, float *cost_out, int *iters_out, int *converged_out) {
    float P[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    float q[2] = {0.0f, 0.0f};
    float l[2] = {0.0f, 0.0f};
    float u[2] = {0.0f, 0.0f};

    int rc = assemble_acc_qp(x, u_prev, w, P, q, l, u);
    if (rc != 0) {
        return rc;
    }

    float v = x[2];
    float h = x[1];
    float sol[2] = {
        MAX(0.0f, MIN(u_prev[0], F_ACCEL_MAX)),
        MAX(0.0f, MIN(u_prev[1], F_BRAKE_MAX))
    };

    QPSettings settings;
    settings.max_iter = 60;
    settings.tol = 1e-3f;
    settings.alpha = 0.05f;

    QPInfo info;
    rc = qp_solve(P, q, l, u, sol, 2, &settings, &info);
    if (rc != 0) {
        return rc;
    }

    float closing_end = 0.0f;
    float margin = predict_terminal_margin(x, sol, w, &closing_end);

    if (margin < MPC_MARGIN_TRIGGER && closing_end > 0.0f) {
        float safety_floor = MPC_SAFETY_CLOSE_GAIN * closing_end + MPC_SAFETY_MARGIN_GAIN * (-margin);
        safety_floor = MIN(F_BRAKE_MAX, MAX(0.0f, safety_floor));
        sol[1] = MAX(sol[1], safety_floor);
        sol[0] = 0.0f;
    }

    if (MPC_TRANSITION_GUARD_ENABLE &&
        h > MPC_TRANSITION_H_MIN && h < MPC_TRANSITION_H_MAX &&
        v > (w[0] + MPC_TRANSITION_VDIFF_MIN)) {
        float v_diff = v - w[0];
        float transition_floor = MPC_TRANSITION_BRAKE_K * v_diff + MPC_TRANSITION_BRAKE_B;
        transition_floor = MIN(F_BRAKE_MAX, MAX(0.0f, transition_floor));
        sol[1] = MAX(sol[1], transition_floor);
        sol[0] = 0.0f;
    }

    if (margin > MPC_BRAKE_CAP_MARGIN_POS && closing_end <= 0.0f) {
        float brake_cap = MPC_BRAKE_CAP_BASE +
                          MPC_BRAKE_CAP_SPEED_GAIN * MAX(0.0f, v - 8.0f) -
                          MPC_BRAKE_CAP_MARGIN_SLOPE * (margin - MPC_BRAKE_CAP_MARGIN_POS);
        brake_cap = MAX(MPC_BRAKE_CAP_MIN, MIN(brake_cap, MPC_BRAKE_CAP_MAX));
        sol[1] = MIN(sol[1], brake_cap);
    }

    u_out[0] = sol[0];
    u_out[1] = sol[1];
    *cost_out = info.obj_val;
    *iters_out = info.iterations;
    *converged_out = info.converged;
    return 0;
}
