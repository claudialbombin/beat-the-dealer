# ============================================================================
# Blackjack Monte Carlo Solver - C Version
# ============================================================================
# Build system for compiling all source files with strict C11 compliance.
#
# Design Constraints Met:
# - Maximum 5 functions per source file
# - Maximum 25 lines per function
# - All structures use static memory allocation
# - No external library dependencies beyond standard C
#
# Usage:
#   make          - Compile the project
#   make run      - Compile and execute full analysis
#   make strategy - Run basic strategy computation only
#   make counting - Run card counting simulation only
#   make viz      - Generate visualizations only
#   make clean    - Remove object files and executable
#   make distclean - Remove all generated files including outputs
#   make help     - Display this help message
#
# Author: Claudia Maria Lopez Bombin
# License: MIT
# Repository: github.com/claudia-lopez/blackjack-monte-carlo
# ============================================================================

# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=c11 -Iinclude
LDFLAGS = -lm

# Directory structure
SRC_DIR = src
INC_DIR = include
OBJ_DIR = obj
BIN_DIR = bin
OUT_DIR = output

# All source files (16 files, each with ≤5 functions)
SOURCES = $(SRC_DIR)/card_utils.c \
          $(SRC_DIR)/hand_utils.c \
          $(SRC_DIR)/shoe_utils.c \
          $(SRC_DIR)/game_actions.c \
          $(SRC_DIR)/game_dealer.c \
          $(SRC_DIR)/game_round.c \
          $(SRC_DIR)/monte_carlo_core.c \
          $(SRC_DIR)/monte_carlo_simulation.c \
          $(SRC_DIR)/monte_carlo_solver.c \
          $(SRC_DIR)/counting_core.c \
          $(SRC_DIR)/counting_simulation.c \
          $(SRC_DIR)/betting_core.c \
          $(SRC_DIR)/visual_strategy.c \
          $(SRC_DIR)/visual_ev.c \
          $(SRC_DIR)/visual_distribution.c \
          $(SRC_DIR)/main.c

# Generate object file paths from source file paths
OBJECTS = $(patsubst $(SRC_DIR)/%.c, $(OBJ_DIR)/%.o, $(SOURCES))

# Final executable
TARGET = $(BIN_DIR)/blackjack_solver

# ============================================================================
# Primary targets
# ============================================================================

# Default: compile everything
all: dirs $(TARGET)
	@echo ""
	@echo "Build complete: $(TARGET)"
	@echo "Run with: make run"
	@echo ""

# Create necessary directories
dirs:
	@mkdir -p $(OBJ_DIR)
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(OUT_DIR)

# Link all object files into final executable
$(TARGET): $(OBJECTS)
	@echo "Linking $(TARGET)..."
	$(CC) $(OBJECTS) -o $(TARGET) $(LDFLAGS)
	@echo "Executable created: $(TARGET)"

# Compile each source file into object file
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

# ============================================================================
# Execution targets
# ============================================================================

# Run complete analysis (strategy + counting + visualizations)
run: $(TARGET)
	@echo ""
	@echo "Running complete analysis..."
	@echo ""
	./$(TARGET)

# Run basic strategy computation only
strategy: $(TARGET)
	@echo ""
	@echo "Building basic strategy..."
	@echo ""
	./$(TARGET) --strategy

# Run card counting simulation only
counting: $(TARGET)
	@echo ""
	@echo "Simulating card counting..."
	@echo ""
	./$(TARGET) --counting

# Generate visualizations only
viz: $(TARGET)
	@echo ""
	@echo "Generating visualizations..."
	@echo ""
	./$(TARGET) --viz

# Run quick demo with reduced simulations
quick: CFLAGS += -DQUICK_MODE
quick: clean all
	@echo ""
	@echo "Running in QUICK mode (reduced simulations)..."
	@echo ""
	./$(TARGET)

# ============================================================================
# Utility targets
# ============================================================================

# Remove object files and executable
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(OBJ_DIR)
	rm -rf $(BIN_DIR)
	@echo "Clean complete."

# Remove everything including generated outputs
distclean: clean
	@echo "Removing all generated files..."
	rm -rf $(OUT_DIR)
	rm -f strategy_cache.dat
	@echo "Distclean complete."

# Verify source file structure constraints
check:
	@echo "Checking project constraints..."
	@echo ""
	@echo "Files (should be 16 .c files):"
	@ls -1 $(SRC_DIR)/*.c | wc -l
	@echo ""
	@echo "Functions per file (should be ≤5):"
	@for file in $(SOURCES); do \
		count=$$(grep -c '^{' $$file 2>/dev/null || echo 0); \
		printf "  %-30s : %d functions\n" $$(basename $$file) $$count; \
	done
	@echo ""
	@echo "Lines per function check..."
	@echo "  (Manual review recommended for 25-line limit)"

# Display help
help:
	@echo ""
	@echo "Blackjack Monte Carlo Solver - Build System"
	@echo "============================================"
	@echo ""
	@echo "BUILD TARGETS:"
	@echo "  make          - Compile the project"
	@echo "  make all      - Same as make (compile everything)"
	@echo ""
	@echo "EXECUTION TARGETS:"
	@echo "  make run      - Run complete analysis"
	@echo "  make strategy - Build basic strategy only"
	@echo "  make counting - Simulate card counting only"
	@echo "  make viz      - Generate visualizations only"
	@echo "  make quick    - Fast mode with fewer simulations"
	@echo ""
	@echo "CLEANUP TARGETS:"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make distclean - Remove everything generated"
	@echo ""
	@echo "UTILITY TARGETS:"
	@echo "  make check    - Verify project constraints"
	@echo "  make help     - Show this message"
	@echo ""

# ============================================================================
# Phony targets (not real files)
# ============================================================================

.PHONY: all dirs run strategy counting viz quick clean distclean check help