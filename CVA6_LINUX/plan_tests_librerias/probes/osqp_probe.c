#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>

#include "osqp.h"

int main(void) {
    c_float P_x[3] = {4.0, 1.0, 2.0};
    c_int   P_i[3] = {0, 0, 1};
    c_int   P_p[3] = {0, 1, 3};

    c_float q[2] = {1.0, 1.0};

    c_float A_x[4] = {1.0, 1.0, 1.0, 1.0};
    c_int   A_i[4] = {0, 1, 0, 2};
    c_int   A_p[3] = {0, 2, 4};

    c_float l[3] = {1.0, 0.0, 0.0};
    c_float u[3] = {1.0, 0.7, 0.7};

    c_int n = 2;
    c_int m = 3;
    c_int exitflag = 0;

    OSQPWorkspace *work = OSQP_NULL;
    OSQPSettings  *settings = (OSQPSettings *)c_malloc(sizeof(OSQPSettings));
    OSQPData      *data = (OSQPData *)c_malloc(sizeof(OSQPData));

    if (!settings || !data) {
        fprintf(stderr, "OSQP_PROBE_ALLOC_FAIL\n");
        return 2;
    }

    data->n = n;
    data->m = m;
    data->P = csc_matrix(data->n, data->n, 3, P_x, P_i, P_p);
    data->q = q;
    data->A = csc_matrix(data->m, data->n, 4, A_x, A_i, A_p);
    data->l = l;
    data->u = u;

    osqp_set_default_settings(settings);
    settings->alpha = 1.0;
    settings->verbose = 0;

    exitflag = osqp_setup(&work, data, settings);
    if (exitflag != 0 || !work) {
        fprintf(stderr, "OSQP_PROBE_SETUP_FAIL=%d\n", (int)exitflag);
        if (data->A) c_free(data->A);
        if (data->P) c_free(data->P);
        c_free(data);
        c_free(settings);
        return 3;
    }

    exitflag = osqp_solve(work);
    if (exitflag != 0) {
        fprintf(stderr, "OSQP_PROBE_SOLVE_FAIL=%d\n", (int)exitflag);
        osqp_cleanup(work);
        if (data->A) c_free(data->A);
        if (data->P) c_free(data->P);
        c_free(data);
        c_free(settings);
        return 4;
    }

    printf("OSQP_PROBE_OK\n");
    printf("status_val=%d\n", (int)work->info->status_val);
    printf("iter=%d\n", (int)work->info->iter);
    printf("obj_val=%.12f\n", (double)work->info->obj_val);
    printf("x0=%.12f\n", (double)work->solution->x[0]);
    printf("x1=%.12f\n", (double)work->solution->x[1]);
    printf("y0=%.12f\n", (double)work->solution->y[0]);
    printf("y1=%.12f\n", (double)work->solution->y[1]);
    printf("y2=%.12f\n", (double)work->solution->y[2]);

    osqp_cleanup(work);
    if (data->A) c_free(data->A);
    if (data->P) c_free(data->P);
    c_free(data);
    c_free(settings);

    return 0;
}
