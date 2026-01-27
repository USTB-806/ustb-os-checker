TARGET := riscv64-unknown-elf
CC := clang --target=$(TARGET)
LD := $(TARGET)-ld
OBJDUMP := $(TARGET)-objdump

CFLAGS := -Wall -Werror -O2 -fno-builtin -nostdlib -mcmodel=medany -march=rv64gc -mabi=lp64 -Ilib
LDFLAGS := -T ../linker.ld

OUT_DIR := ../build

SRCS := $(wildcard apps/*.c)
APPS := $(patsubst apps/%.c,%,$(SRCS))

all: $(OUT_DIR) $(addprefix $(OUT_DIR)/,$(APPS))

$(OUT_DIR):
	mkdir -p $(OUT_DIR)

lib.o: lib/lib.c lib/lib.h
	$(CC) $(CFLAGS) -c lib/lib.c -o lib.o

$(OUT_DIR)/%: apps/%.c lib.o ../linker.ld | $(OUT_DIR)
	$(CC) $(CFLAGS) -c $< -o $*.o
	$(LD) $(LDFLAGS) -o $@ $*.o lib.o
	$(OBJDUMP) -S $@ > $@.asm
	@rm -f $*.o

clean:
	rm -f *.o
