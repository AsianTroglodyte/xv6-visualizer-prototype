#include "kernel/types.h"
#include "user/user.h"

int
main(int argc, char **argv)
{
  int ticks = 20;

  if (argc > 1)
    ticks = atoi(argv[1]);
  if (ticks < 1)
    ticks = 1;

  pause(ticks);
  exit(0);
}
