#ifndef EXAMPLE_DISPLAY_H
#define EXAMPLE_DISPLAY_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void display_init(void);
size_t display_write(const char *text, size_t size);

#ifdef __cplusplus
}
#endif

#endif
