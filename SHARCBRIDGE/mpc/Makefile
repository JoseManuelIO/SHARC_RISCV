################################################################################
# Makefile para MPC ACC Controller - SHARCBRIDGE
# Solver: Custom QP (Projected Gradient Descent)
################################################################################

APP ?= mpc_acc_controller

ifeq ($(APP),mpc_acc_controller)
APP_SRCS = start.S mpc_acc_controller.c qp_solver.c
else ifeq ($(APP),qp_riscv_runtime)
APP_SRCS = start.S qp_riscv_runtime.c
else
$(error Unsupported APP='$(APP)'. Use mpc_acc_controller or qp_riscv_runtime)
endif

# Paths
PULP_SDK_HOME ?= $(HOME)/Repositorios/SHARC_RISCV/PULP/pulp-sdk
TOOLCHAIN_DIR = /opt/riscv
BUILD_DIR = build

# Tools
CC = $(TOOLCHAIN_DIR)/bin/riscv32-unknown-elf-gcc
LD = $(TOOLCHAIN_DIR)/bin/riscv32-unknown-elf-gcc
SIZE = $(TOOLCHAIN_DIR)/bin/riscv32-unknown-elf-size
OBJDUMP = $(TOOLCHAIN_DIR)/bin/riscv32-unknown-elf-objdump

# Compiler flags
# Select numeric/ISA profile without changing default behavior.
# - single: current baseline (rv32imcxpulpv2 + ilp32)
# - double: enable D extension and hard-float double ABI
SHARC_NUMERIC_PROFILE ?= single

ifeq ($(SHARC_NUMERIC_PROFILE),double)
MARCH ?= rv32imfdcxpulpv2
MABI ?= ilp32d
USER_DEFINES += -DSHARC_MPC_DOUBLE=1
else ifeq ($(SHARC_NUMERIC_PROFILE),single)
MARCH ?= rv32imcxpulpv2
MABI ?= ilp32
else
$(error Unsupported SHARC_NUMERIC_PROFILE='$(SHARC_NUMERIC_PROFILE)'. Use single or double)
endif

ARCH_FLAGS = -march=$(MARCH) -mabi=$(MABI)
OPT_FLAGS = -Os -g
WARN_FLAGS = -Wall -Wextra

DEFINES = \
	-DPULP_CHIP=PULP \
	-DPULP_CHIP_STR=pulp \
	-DCHIP_PULP=1 \
	-D__PULP__ \
	-D__RISCV__

USER_DEFINES ?=

INCLUDES = \
	-I$(CURDIR) \
	-I$(PULP_SDK_HOME)/rtos/pulpos/common/include \
	-I$(PULP_SDK_HOME)/rtos/pmsis/pmsis_api/include \
	-I$(PULP_SDK_HOME)/rtos/pmsis/pmsis_bsp/include \
	-I$(PULP_SDK_HOME)/rtos/pulpos/pulp_hal/include \
	-I$(PULP_SDK_HOME)/rtos/pulpos/pulp_hal/include/hal/chips/pulp \
	-I$(PULP_SDK_HOME)/rtos/pulpos/pulp_archi/include \
	-I$(PULP_SDK_HOME)/rtos/pulpos/pulp_archi/include/archi/chips/pulp

LINKER_SCRIPT = $(CURDIR)/riscv.ld

CFLAGS = $(ARCH_FLAGS) $(OPT_FLAGS) $(WARN_FLAGS) $(DEFINES) $(USER_DEFINES) $(INCLUDES)
LDFLAGS = $(ARCH_FLAGS) -T$(LINKER_SCRIPT) -nostartfiles -Wl,-Map=$(BUILD_DIR)/$(APP).map
LDLIBS = -lm -lgcc

# Object files
OBJS = $(addprefix $(BUILD_DIR)/,$(APP_SRCS:.c=.o))
OBJS := $(OBJS:.S=.o)

# Targets
.PHONY: all clean dump info

all: $(BUILD_DIR)/$(APP).elf
	@echo ""
	@echo "════════════════════════════════════════════════════════"
	@echo "✓ Build complete: $(BUILD_DIR)/$(APP).elf"
	@echo "════════════════════════════════════════════════════════"
	@$(SIZE) $<
	@echo "════════════════════════════════════════════════════════"

$(BUILD_DIR)/$(APP).elf: $(OBJS) $(LINKER_SCRIPT) | $(BUILD_DIR)
	@echo "[LD] Linking $(APP).elf"
	@$(LD) $(LDFLAGS) $(OBJS) $(LDLIBS) -o $@

$(BUILD_DIR)/start.o: start.S | $(BUILD_DIR)
	@echo "[AS] $<"
	@$(CC) $(ARCH_FLAGS) $(DEFINES) $(USER_DEFINES) -c $< -o $@

$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	@echo "[CC] $<"
	@$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR):
	@mkdir -p $@

clean:
	@rm -rf $(BUILD_DIR)
	@echo "✓ Clean complete"

dump: $(BUILD_DIR)/$(APP).elf
	@$(OBJDUMP) -d $< > $(BUILD_DIR)/$(APP).asm
	@echo "✓ Disassembly: $(BUILD_DIR)/$(APP).asm"

info: $(BUILD_DIR)/$(APP).elf
	@echo "ELF Information:"
	@file $<
	@echo ""
	@$(SIZE) -A $<
