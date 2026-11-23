#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
  puts("Hello from mruby/c");
  vTaskDelay(pdMS_TO_TICKS(50));
  puts("Timer wakeup complete");
  puts("mruby/c scheduler finished");
}
