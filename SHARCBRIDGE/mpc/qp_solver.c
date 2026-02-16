#include "qp_solver.h"
#include <math.h>

// Forward declarations for print functions
extern void print(const char *str);
extern void print_int(int val);
extern void print_float(float val);

// Project x onto box constraints [l, u]
static void project_box(float *x, const float *l, const float *u, int n) {
    for (int i = 0; i < n; i++) {
        if (x[i] < l[i]) x[i] = l[i];
        if (x[i] > u[i]) x[i] = u[i];
    }
}

// Compute gradient: grad = P*x + q
static void compute_gradient(const float *P, const float *q, const float *x,
                            float *grad, int n) {
    // grad = P*x + q
    for (int i = 0; i < n; i++) {
        grad[i] = q[i];
        for (int j = 0; j < n; j++) {
            grad[i] += P[i * n + j] * x[j];
        }
    }
}

// Compute objective: 0.5*x'*P*x + q'*x
static float compute_objective(const float *P, const float *q, const float *x, int n) {
    float obj = 0.0f;
    
    // Linear term: q'*x
    for (int i = 0; i < n; i++) {
        obj += q[i] * x[i];
    }
    
    // Quadratic term: 0.5*x'*P*x
    for (int i = 0; i < n; i++) {
        float Px_i = 0.0f;
        for (int j = 0; j < n; j++) {
            Px_i += P[i * n + j] * x[j];
        }
        obj += 0.5f * x[i] * Px_i;
    }
    
    return obj;
}

// Solve QP using Projected Gradient Descent with Backtracking Line Search
int qp_solve(const float *P, const float *q, 
             const float *l, const float *u,
             float *x, int n,
             const QPSettings *settings,
             QPInfo *info) {
    
    // Allocate workspace (max n=10 for MPC)
    #define MAX_QP_N 20
    static float grad[MAX_QP_N];
    static float x_new[MAX_QP_N];
    
    if (n > MAX_QP_N) {
        return -1;  // Problem too large
    }
    
    // Initialize
    int max_iter = settings->max_iter;
    float tol = settings->tol;
    float alpha = settings->alpha;
    
    // Project initial guess
    project_box(x, l, u, n);
    
    // Main iteration loop
    for (int iter = 0; iter < max_iter; iter++) {
        // Compute gradient at current point
        compute_gradient(P, q, x, grad, n);
        
        // Backtracking line search
        float step = alpha;
        float obj_current = compute_objective(P, q, x, n);
        int ls_iter = 0;
        const int max_ls_iter = 20;
        const float beta = 0.5f;  // Step size reduction factor
        const float c1 = 0.1f;    // Armijo condition parameter
        
        // Compute search direction (projected gradient)
        float grad_norm_sq = 0.0f;
        for (int i = 0; i < n; i++) {
            grad_norm_sq += grad[i] * grad[i];
        }
        
        // Check convergence
        if (grad_norm_sq < tol * tol) {
            info->obj_val = obj_current;
            info->iterations = iter;
            info->converged = 1;
            
            if (settings->verbose) {
                print("[QP] Converged in "); print_int(iter); 
                print(" iterations, obj="); print_float(obj_current); print("\n");
            }
            return 0;
        }
        
        // Line search: find step size
        while (ls_iter < max_ls_iter) {
            // Take step: x_new = x - step * grad
            for (int i = 0; i < n; i++) {
                x_new[i] = x[i] - step * grad[i];
            }
            
            // Project onto constraints
            project_box(x_new, l, u, n);
            
            // Compute new objective
            float obj_new = compute_objective(P, q, x_new, n);
            
            // Armijo condition (sufficient decrease)
            float decrease = 0.0f;
            for (int i = 0; i < n; i++) {
                decrease += grad[i] * (x[i] - x_new[i]);
            }
            
            if (obj_new <= obj_current - c1 * decrease) {
                // Accept step
                break;
            }
            
            // Reduce step size
            step *= beta;
            ls_iter++;
        }
        
        // Update x
        for (int i = 0; i < n; i++) {
            x[i] = x_new[i];
        }
        
        // Debug output every 10 iterations
        if (settings->verbose && (iter % 10 == 0)) {
            float obj = compute_objective(P, q, x, n);
            print("[QP] Iter "); print_int(iter);
            print(", obj="); print_float(obj);
            print(", |grad|²="); print_float(grad_norm_sq); print("\n");
        }
    }
    
    // Did not converge
    info->obj_val = compute_objective(P, q, x, n);
    info->iterations = max_iter;
    info->converged = 0;
    
    if (settings->verbose) {
        print("[QP] Max iterations reached, obj="); 
        print_float(info->obj_val); print("\n");
    }
    
    return 0;  // Success (even if not fully converged)
}
