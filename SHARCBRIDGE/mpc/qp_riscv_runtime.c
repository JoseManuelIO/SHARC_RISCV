/*
 * QP Runtime Solver for RISC-V/GVSoC.
 *
 * Solves generic QP payloads of form:
 *   minimize 0.5*x'Px + q'x
 *   subject to l <= A x <= u
 *
 * Uses deterministic ADMM with dense math (bounded dimensions).
 */

#include <stdint.h>
#include <math.h>

#define STDOUT_BASE 0x1A10F000
volatile uint32_t *const stdout_reg = (uint32_t *)STDOUT_BASE;

#define APB_SOC_CORESTATUS (*(volatile uint32_t *)0x1A1040A0)

static inline void terminate_simulation(int status)
{
    APB_SOC_CORESTATUS = (1U << 31) | (status & 0x7FFFFFFF);
    while (1) {
    }
}

static void putchar_hw(char c)
{
    *stdout_reg = (uint32_t)c;
}

static void print(const char *s)
{
    while (*s) {
        putchar_hw(*s++);
    }
}

static void print_int(int v)
{
    if (v == 0) {
        putchar_hw('0');
        return;
    }

    if (v < 0) {
        putchar_hw('-');
        v = -v;
    }

    char b[16];
    int i = 0;
    while (v > 0) {
        b[i++] = (char)('0' + (v % 10));
        v /= 10;
    }
    while (i > 0) {
        putchar_hw(b[--i]);
    }
}

static void print_float6(float val)
{
    if (val < 0.0f) {
        putchar_hw('-');
        val = -val;
    }

    int ip = (int)val;
    float frac = val - (float)ip;
    int fp = (int)(frac * 1000000.0f + 0.5f);

    if (fp >= 1000000) {
        ip += 1;
        fp -= 1000000;
    }

    print_int(ip);
    putchar_hw('.');

    int scale = 100000;
    while (scale > 0) {
        int digit = fp / scale;
        putchar_hw((char)('0' + digit));
        fp -= digit * scale;
        scale /= 10;
    }
}

static inline unsigned int read_cycle_counter(void)
{
    unsigned int cycles;
    __asm__ volatile("rdcycle %0" : "=r"(cycles));
    return cycles;
}

/* PULP performance counters (PCER/PCMR + PCCR[x]). */
#define CSR_PCER 0xCC0
#define CSR_PCMR 0xCC1
#define CSR_PCCR_BASE 0x780
#define CSR_PCCR_SETALL 0x79F

#define PCMR_ACTIVE 0x1
#define PCMR_SATURATE 0x2

#define PCER_INSTR 1
#define PCER_LD_STALL 2
#define PCER_JMP_STALL 3
#define PCER_IMISS 4
#define PCER_BRANCH 8
#define PCER_TAKEN_BRANCH 9

static inline void perf_conf_events(unsigned int mask)
{
    __asm__ volatile("csrw %0, %1" :: "i"(CSR_PCER), "r"(mask));
}

static inline void perf_conf_mode(unsigned int mode)
{
    __asm__ volatile("csrw %0, %1" :: "i"(CSR_PCMR), "r"(mode));
}

static inline void perf_set_all(unsigned int value)
{
    __asm__ volatile("csrw %0, %1" :: "i"(CSR_PCCR_SETALL), "r"(value));
}

static inline unsigned int perf_get_counter(unsigned int counter_id)
{
    unsigned int value = 0;
    switch (counter_id) {
    case 0:
        __asm__ volatile("csrr %0, 0x780" : "=r"(value));
        break;
    case 1:
        __asm__ volatile("csrr %0, 0x781" : "=r"(value));
        break;
    case 2:
        __asm__ volatile("csrr %0, 0x782" : "=r"(value));
        break;
    case 3:
        __asm__ volatile("csrr %0, 0x783" : "=r"(value));
        break;
    case 4:
        __asm__ volatile("csrr %0, 0x784" : "=r"(value));
        break;
    case 8:
        __asm__ volatile("csrr %0, 0x788" : "=r"(value));
        break;
    case 9:
        __asm__ volatile("csrr %0, 0x789" : "=r"(value));
        break;
    default:
        break;
    }
    return value;
}

static inline void perf_start_for_qp(void)
{
    unsigned int mask = 0;
    mask |= (1U << PCER_INSTR);
    mask |= (1U << PCER_LD_STALL);
    mask |= (1U << PCER_JMP_STALL);
    mask |= (1U << PCER_IMISS);
    mask |= (1U << PCER_BRANCH);
    mask |= (1U << PCER_TAKEN_BRANCH);
    perf_conf_events(mask);
    perf_set_all(0U);
    perf_conf_mode(PCMR_ACTIVE | PCMR_SATURATE);
}

static inline void perf_stop(void)
{
    perf_conf_mode(0U);
}

#define QP_MAX_N 32
#define QP_MAX_M 64

#define QP_STATUS_OPTIMAL 0
#define QP_STATUS_MAX_ITER 1
#define QP_STATUS_BAD_DIM -1
#define QP_STATUS_FACTOR_FAIL -2

typedef struct __attribute__((packed)) {
    int32_t n;
    int32_t m;
    float P[QP_MAX_N * QP_MAX_N];
    float q[QP_MAX_N];
    float A[QP_MAX_M * QP_MAX_N];
    float l[QP_MAX_M];
    float u[QP_MAX_M];
    float x0[QP_MAX_N];
    int32_t max_iter;
    float tol;
    float rho;
    float sigma;

    float x[QP_MAX_N];
    float cost;
    float primal_residual;
    float dual_residual;
    int32_t iterations;
    int32_t converged;
    int32_t status;
    int32_t output_n;
    int32_t output_m;
    int32_t output_cycles;
    int32_t done_flag;
    int32_t runtime_mode; /* 0=single-shot (legacy), 1=persistent loop */
    int32_t heartbeat;
    int32_t output_instret;
    int32_t output_ld_stall;
    int32_t output_jmp_stall;
    int32_t output_stall_total;
    int32_t output_imiss;
    int32_t output_branch;
    int32_t output_taken_branch;
} QPSharedData;

volatile QPSharedData shared __attribute__((section(".shared_data"))) = {
    .n = 0,
    .m = 0,
    .max_iter = 80,
    .tol = 1e-5f,
    .rho = 0.1f,
    .sigma = 1e-8f,
    .done_flag = 0,
    .runtime_mode = 0,
    .heartbeat = 0,
};

static float vec_norm(const float *v, int n)
{
    float s = 0.0f;
    for (int i = 0; i < n; i++) {
        s += v[i] * v[i];
    }
    return sqrtf(s);
}

static void matvec_row_major(const float *A, int rows, int cols, const float *x, float *out)
{
    for (int r = 0; r < rows; r++) {
        float acc = 0.0f;
        int base = r * cols;
        for (int c = 0; c < cols; c++) {
            acc += A[base + c] * x[c];
        }
        out[r] = acc;
    }
}

static void mat_t_vec_row_major(const float *A, int rows, int cols, const float *y, float *out)
{
    for (int c = 0; c < cols; c++) {
        out[c] = 0.0f;
    }
    for (int r = 0; r < rows; r++) {
        float yr = y[r];
        int base = r * cols;
        for (int c = 0; c < cols; c++) {
            out[c] += A[base + c] * yr;
        }
    }
}

static void clip_vec(float *x, const float *lo, const float *hi, int n)
{
    for (int i = 0; i < n; i++) {
        if (x[i] < lo[i]) x[i] = lo[i];
        if (x[i] > hi[i]) x[i] = hi[i];
    }
}

static float objective(const float *P, const float *q, const float *x, int n)
{
    float quad = 0.0f;
    float lin = 0.0f;
    for (int i = 0; i < n; i++) {
        float pxi = 0.0f;
        for (int j = 0; j < n; j++) {
            pxi += P[i * n + j] * x[j];
        }
        quad += x[i] * pxi;
        lin += q[i] * x[i];
    }
    return 0.5f * quad + lin;
}

static int cholesky_decompose(const float *A, float *L, int n)
{
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
                if (sum <= 1e-10f) {
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

static void cholesky_solve(const float *L, const float *b, float *x, int n)
{
    float y[QP_MAX_N];

    for (int i = 0; i < n; i++) {
        float sum = b[i];
        for (int k = 0; k < i; k++) {
            sum -= L[i * n + k] * y[k];
        }
        y[i] = sum / L[i * n + i];
    }

    for (int i = n - 1; i >= 0; i--) {
        float sum = y[i];
        for (int k = i + 1; k < n; k++) {
            sum -= L[k * n + i] * x[k];
        }
        x[i] = sum / L[i * n + i];
    }
}

static void solve_qp_runtime(void)
{
    int n = shared.n;
    int m = shared.m;

    shared.output_n = n;
    shared.output_m = m;
    shared.status = QP_STATUS_BAD_DIM;
    shared.iterations = 0;
    shared.converged = 0;
    shared.primal_residual = 0.0f;
    shared.dual_residual = 0.0f;
    shared.output_instret = 0;
    shared.output_ld_stall = 0;
    shared.output_jmp_stall = 0;
    shared.output_stall_total = 0;
    shared.output_imiss = 0;
    shared.output_branch = 0;
    shared.output_taken_branch = 0;

    if (n <= 0 || m <= 0 || n > QP_MAX_N || m > QP_MAX_M) {
        return;
    }

    float rho = shared.rho;
    float sigma = shared.sigma;
    float tol = shared.tol;
    int max_iter = shared.max_iter;

    if (rho <= 0.0f) rho = 0.1f;
    if (sigma < 0.0f) sigma = 1e-8f;
    if (tol <= 0.0f) tol = 1e-5f;
    if (max_iter <= 0) max_iter = 80;

    float K[QP_MAX_N * QP_MAX_N];
    float L[QP_MAX_N * QP_MAX_N];
    float rhs[QP_MAX_N];

    float x[QP_MAX_N];
    float Ax[QP_MAX_M];
    float z[QP_MAX_M];
    float z_prev[QP_MAX_M];
    float y[QP_MAX_M];
    float tmp_m[QP_MAX_M];
    float At_tmp[QP_MAX_N];
    float At_dz[QP_MAX_N];

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            float ata = 0.0f;
            for (int k = 0; k < m; k++) {
                ata += shared.A[k * n + i] * shared.A[k * n + j];
            }
            K[i * n + j] = shared.P[i * n + j] + rho * ata;
        }
        K[i * n + i] += sigma;
    }

    if (cholesky_decompose(K, L, n) != 0) {
        shared.status = QP_STATUS_FACTOR_FAIL;
        return;
    }

    for (int i = 0; i < n; i++) {
        x[i] = shared.x0[i];
    }

    matvec_row_major((const float *)shared.A, m, n, x, Ax);
    for (int i = 0; i < m; i++) {
        z[i] = Ax[i];
        y[i] = 0.0f;
    }
    clip_vec(z, (const float *)shared.l, (const float *)shared.u, m);

    float primal_res = 1e30f;
    float dual_res = 1e30f;
    int converged = 0;
    int iterations = max_iter;

    for (int it = 0; it < max_iter; it++) {
        for (int i = 0; i < m; i++) {
            tmp_m[i] = z[i] - y[i];
        }
        mat_t_vec_row_major((const float *)shared.A, m, n, tmp_m, At_tmp);
        for (int i = 0; i < n; i++) {
            rhs[i] = rho * At_tmp[i] - shared.q[i];
        }
        cholesky_solve(L, rhs, x, n);

        matvec_row_major((const float *)shared.A, m, n, x, Ax);
        for (int i = 0; i < m; i++) {
            z_prev[i] = z[i];
            z[i] = Ax[i] + y[i];
        }
        clip_vec(z, (const float *)shared.l, (const float *)shared.u, m);

        for (int i = 0; i < m; i++) {
            y[i] += Ax[i] - z[i];
            tmp_m[i] = Ax[i] - z[i];
        }
        primal_res = vec_norm(tmp_m, m);

        for (int i = 0; i < m; i++) {
            tmp_m[i] = z[i] - z_prev[i];
        }
        mat_t_vec_row_major((const float *)shared.A, m, n, tmp_m, At_dz);
        for (int i = 0; i < n; i++) {
            At_dz[i] *= rho;
        }
        dual_res = vec_norm(At_dz, n);

        if (primal_res <= tol && dual_res <= tol) {
            converged = 1;
            iterations = it + 1;
            break;
        }
    }

    for (int i = 0; i < n; i++) {
        shared.x[i] = x[i];
    }
    shared.cost = objective((const float *)shared.P, (const float *)shared.q, x, n);
    shared.primal_residual = primal_res;
    shared.dual_residual = dual_res;
    shared.iterations = iterations;
    shared.converged = converged;
    shared.status = converged ? QP_STATUS_OPTIMAL : QP_STATUS_MAX_ITER;
}

int main(void)
{
    if (shared.runtime_mode == 1) {
        /*
         * Persistent mode:
         * - Host writes full payload and sets done_flag=0 to request a solve.
         * - Runtime solves once and sets done_flag=1 when outputs are ready.
         */
        while (1) {
            shared.heartbeat += 1;
            if (shared.done_flag == 0) {
                perf_start_for_qp();
                unsigned int c0 = read_cycle_counter();
                solve_qp_runtime();
                unsigned int c1 = read_cycle_counter();
                perf_stop();
                shared.output_cycles = (int32_t)(c1 - c0);
                shared.output_instret = (int32_t)perf_get_counter(PCER_INSTR);
                shared.output_ld_stall = (int32_t)perf_get_counter(PCER_LD_STALL);
                shared.output_jmp_stall = (int32_t)perf_get_counter(PCER_JMP_STALL);
                shared.output_imiss = (int32_t)perf_get_counter(PCER_IMISS);
                shared.output_branch = (int32_t)perf_get_counter(PCER_BRANCH);
                shared.output_taken_branch = (int32_t)perf_get_counter(PCER_TAKEN_BRANCH);
                shared.output_stall_total = shared.output_ld_stall + shared.output_jmp_stall + shared.output_imiss;
                shared.done_flag = 1;
            }
        }
    }

    /* Legacy single-shot mode: keep textual output contract unchanged. */
    print("QP_START\n");

    perf_start_for_qp();
    unsigned int c0 = read_cycle_counter();
    solve_qp_runtime();
    unsigned int c1 = read_cycle_counter();
    perf_stop();

    shared.output_cycles = (int32_t)(c1 - c0);
    shared.output_instret = (int32_t)perf_get_counter(PCER_INSTR);
    shared.output_ld_stall = (int32_t)perf_get_counter(PCER_LD_STALL);
    shared.output_jmp_stall = (int32_t)perf_get_counter(PCER_JMP_STALL);
    shared.output_imiss = (int32_t)perf_get_counter(PCER_IMISS);
    shared.output_branch = (int32_t)perf_get_counter(PCER_BRANCH);
    shared.output_taken_branch = (int32_t)perf_get_counter(PCER_TAKEN_BRANCH);
    shared.output_stall_total = shared.output_ld_stall + shared.output_jmp_stall + shared.output_imiss;

    print("N=");
    print_int((int)shared.output_n);
    print("\nM=");
    print_int((int)shared.output_m);
    print("\nX=");
    int n = shared.output_n;
    if (n < 0) n = 0;
    if (n > QP_MAX_N) n = QP_MAX_N;
    for (int i = 0; i < n; i++) {
        print_float6(shared.x[i]);
        if (i + 1 < n) putchar_hw(',');
    }
    print("\nCOST=");
    print_float6(shared.cost);
    print("\nITER=");
    print_int((int)shared.iterations);
    print("\nPRIMAL_RES=");
    print_float6(shared.primal_residual);
    print("\nDUAL_RES=");
    print_float6(shared.dual_residual);
    print("\nCYCLES=");
    print_int((int)shared.output_cycles);
    print("\nINSTRET=");
    print_int((int)shared.output_instret);
    print("\nLD_STALL=");
    print_int((int)shared.output_ld_stall);
    print("\nJMP_STALL=");
    print_int((int)shared.output_jmp_stall);
    print("\nSTALL_TOTAL=");
    print_int((int)shared.output_stall_total);
    print("\nIMISS=");
    print_int((int)shared.output_imiss);
    print("\nBRANCH=");
    print_int((int)shared.output_branch);
    print("\nTAKEN_BRANCH=");
    print_int((int)shared.output_taken_branch);

    print("\nSTATUS=");
    if (shared.status == QP_STATUS_OPTIMAL) {
        print("OPTIMAL\n");
    } else if (shared.status == QP_STATUS_MAX_ITER) {
        print("MAX_ITER\n");
    } else if (shared.status == QP_STATUS_FACTOR_FAIL) {
        print("FACTOR_FAIL\n");
    } else {
        print("BAD_DIM\n");
    }

    shared.done_flag = 1;
    print("QP_DONE\n");

    terminate_simulation(0);
    return 0;
}
