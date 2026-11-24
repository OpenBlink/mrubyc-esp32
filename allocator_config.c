// SPDX-License-Identifier: BSD-3-Clause
_Static_assert(MRBC_MIN_MEMORY_BLOCK_SIZE % 4 == 0,
               "mruby/c minimum pool block size must be a multiple of four bytes.");
_Static_assert(MRBC_MIN_MEMORY_BLOCK_SIZE >= (1U << MRBC_ALLOC_IGNORE_LSBS),
               "mruby/c minimum pool block size must be at least 2 to the power of the ignored bits.");
