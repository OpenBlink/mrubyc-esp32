#include "sdkconfig.h"

#if defined(CONFIG_GPTIMER_ISR_CACHE_SAFE) && !defined(CONFIG_MRUBYC_NO_TIMER)
#error "mruby/c GPTimer callback is not cache-safe. Disable CONFIG_GPTIMER_ISR_CACHE_SAFE or enable CONFIG_MRUBYC_NO_TIMER."
#endif
