#ifndef QP_SOLVER_H
#define QP_SOLVER_H

#ifdef __cplusplus
extern "C" {
#endif

// Lightweight OSQP-style ADMM solver (box constraints only)
// Solves: minimize 0.5*x'*P*x + q'*x
//         subject to: l <= x <= u

typedef struct {
    int max_iter;        // Maximum iterations
    float tol;           // Convergence tolerance
    float alpha;         // ADMM penalty rho (kept name for backward compatibility)
    int verbose;         // Print debug info
} QPSettings;

typedef struct {
    float obj_val;       // Objective value
    int iterations;      // Number of iterations
    int converged;       // 1 if converged, 0 otherwise
} QPInfo;

// Solve QP problem
// P: n×n dense matrix (row-major)
// q: n vector
// l, u: n vectors (lower/upper bounds)
// x: n vector (input: initial guess, output: solution)
// n: problem dimension
int qp_solve(const float *P, const float *q, 
             const float *l, const float *u,
             float *x, int n,
             const QPSettings *settings,
             QPInfo *info);

#ifdef __cplusplus
}
#endif

#endif // QP_SOLVER_H
