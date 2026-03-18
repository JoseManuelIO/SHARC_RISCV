#include "qp_solver.h"
#include <math.h>

// Forward declarations for print functions
extern void print(const char *str);
extern void print_int(int val);
extern void print_float(float val);

#define MAX_QP_N 20

// Project x onto box constraints [l, u]
static void project_box(float *x, const float *l, const float *u, int n) {
    for (int i = 0; i < n; i++) {
        if (x[i] < l[i]) x[i] = l[i];
        if (x[i] > u[i]) x[i] = u[i];
    }
}

// Compute objective: 0.5*x'*P*x + q'*x
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

// Solve (L*L^T)x=b using forward/back substitution.
static void cholesky_solve(const float *L, const float *b, float *x, int n) {
    float y[MAX_QP_N];

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

// Solve QP using a lightweight OSQP-style ADMM formulation for box constraints.
int qp_solve(const float *P, const float *q,
             const float *l, const float *u,
             float *x, int n,
             const QPSettings *settings,
             QPInfo *info) {
    static float K[MAX_QP_N * MAX_QP_N];
    static float L[MAX_QP_N * MAX_QP_N];
    static float rhs[MAX_QP_N];
    static float z[MAX_QP_N];
    static float z_prev[MAX_QP_N];
    static float y[MAX_QP_N];

    if (n <= 0 || n > MAX_QP_N) {
        return -1;
    }

    const int max_iter = (settings && settings->max_iter > 0) ? settings->max_iter : 60;
    const float tol = (settings && settings->tol > 0.0f) ? settings->tol : 1e-3f;
    float rho = (settings && settings->alpha > 0.0f) ? settings->alpha : 0.05f;
    const int verbose = (settings && settings->verbose) ? 1 : 0;

    if (rho < 1e-6f) {
        rho = 1e-6f;
    }

    // Build and factorize K = P + rho*I once.
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            K[i * n + j] = P[i * n + j];
        }
        K[i * n + i] += rho;
    }

    if (cholesky_decompose(K, L, n) != 0) {
        return -2;
    }

    // Warm start.
    project_box(x, l, u, n);
    for (int i = 0; i < n; i++) {
        z[i] = x[i];
        y[i] = 0.0f;
    }

    for (int iter = 0; iter < max_iter; iter++) {
        // x-update: (P + rho I)x = rho(z - y) - q
        for (int i = 0; i < n; i++) {
            rhs[i] = rho * (z[i] - y[i]) - q[i];
        }
        cholesky_solve(L, rhs, x, n);

        // z-update and y-update
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

        if (verbose && (iter % 10 == 0)) {
            float obj = compute_objective(P, q, z, n);
            print("[QP-ADMM] Iter "); print_int(iter);
            print(", obj="); print_float(obj);
            print(", |r|²="); print_float(r_norm_sq);
            print(", |s|²="); print_float(s_norm_sq); print("\n");
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
