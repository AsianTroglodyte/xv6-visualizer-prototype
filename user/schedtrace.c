#include "kernel/types.h"
#include "user/user.h"

int
main(int argc, char **argv)
{
  int delay = 1;

  if (argc > 1)
    delay = atoi(argv[1]);
  if (delay < 1)
    delay = 1;

  for (;;) {
    schedtrace();
    pause(delay);
  }
}
