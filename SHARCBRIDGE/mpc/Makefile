################################################################################
# Makefile para MPC ACC Controller - SHARCBRIDGE
# Solver: Custom QP (Projected Gradient Descent)
################################################################################

APP = mpc_acc_controller
APP_SRCS = start.S mpc_acc_controller.c qp_solver.c

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
ARCH_FLAGS = -march=rv32imcxpulpv2 -mabi=ilp32
OPT_FLAGS = -Os -g
WARN_FLAGS = -Wall -Wextra

DEFINES = \
	-DPULP_CHIP=PULP \
	-DPULP_CHIP_STR=pulp \
	-DCHIP_PULP=1 \
	-D__PULP__ \
	-D__RISCV__

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

CFLAGS = $(ARCH_FLAGS) $(OPT_FLAGS) $(WARN_FLAGS) $(DEFINES) $(INCLUDES)
LDFLAGS = $(ARCH_FLAGS) -T$(LINKER_SCRIPT) -nostartfiles -Wl,-Map=$(BUILD_DIR)/$(APP).map
LDLIBS = -lm -lgcc

# Object files
OBJS = $(BUILD_DIR)/start.o $(BUILD_DIR)/mpc_acc_controller.o $(BUILD_DIR)/qp_solver.o

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
	@$(CC) $(ARCH_FLAGS) $(DEFINES) -c $< -o $@

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
