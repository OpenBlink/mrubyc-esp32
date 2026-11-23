// SPDX-License-Identifier: BSD-3-Clause
#include "fatal_hooks.h"
#include "mrubyc.h"

#ifdef CONFIG_MRUBYC_OOM_POOL_STATS
void mrubyc_esp32_abort_with_pool_stats(void)
{
  struct MRBC_ALLOC_STATISTICS stats;
  mrbc_alloc_statistics(&stats);
  mrbc_printf("mruby/c pool: total=%u used=%u free=%u bytes\n",
              (int)stats.total, (int)stats.used, (int)stats.free);
  static const char msg[] = "Fatal error: Out of memory.\n";
  hal_write(2, msg, sizeof(msg) - 1);
  hal_abort(NULL);
}
#endif

#ifdef CONFIG_MRUBYC_PANIC_ON_UNHANDLED_EXCEPTION
void mrubyc_esp32_abort_with_exception(const struct VM *vm)
{
  mrbc_print_vm_exception(vm);
  hal_abort(NULL);
}
#endif
