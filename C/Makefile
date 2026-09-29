CC      ?= cc
CFLAGS  ?= -O2 -march=native
CFLAGS  += -std=c11 -Wall -Wextra -Wpedantic -Iinclude -D_POSIX_C_SOURCE=200809L
LDLIBS  += -lm -lpthread

LIB_SRC := src/rng.c src/cards.c src/strategy.c src/round.c
LIB_OBJ := $(LIB_SRC:src/%.c=build/%.o)

.PHONY: all test run clean

all: bin/bjsim

bin/bjsim: $(LIB_OBJ) build/main.o | bin
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

bin/test_bj: $(LIB_OBJ) build/test_bj.o | bin
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

build/%.o: src/%.c include/bj.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/test_bj.o: tests/test_bj.c include/bj.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build bin:
	mkdir -p $@

test: bin/test_bj
	./bin/test_bj

# The run behind web/data/counting.json and the README numbers.
run: bin/bjsim
	./bin/bjsim --rounds 400000000 --threads 8 --out ../results/counting_c.csv

clean:
	rm -rf build bin
