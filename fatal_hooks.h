// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include "sdkconfig.h"

#ifdef CONFIG_MRUBYC_OOM_POOL_STATS
void mrubyc_esp32_abort_with_pool_stats(void);
#define MRBC_OUT_OF_MEMORY() mrubyc_esp32_abort_with_pool_stats()
#endif

#ifdef CONFIG_MRUBYC_PANIC_ON_UNHANDLED_EXCEPTION
struct VM;
void mrubyc_esp32_abort_with_exception(const struct VM *vm);
#define MRBC_ABORT_BY_EXCEPTION(vm) mrubyc_esp32_abort_with_exception(vm)
#endif
