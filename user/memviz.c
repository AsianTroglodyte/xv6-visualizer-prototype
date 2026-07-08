#include "kernel/types.h"
#include "user/user.h"

int
main(int argc, char **argv)
{
  int delay = 20;

  if (argc > 1)
    delay = atoi(argv[1]);

  for (;;) {
    vizsnap();
    pause(delay);
  }
}
