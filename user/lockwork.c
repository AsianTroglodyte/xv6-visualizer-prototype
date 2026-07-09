#include "kernel/types.h"
#include "user/user.h"

static void
spawn_worker(int wave, int slot, int hold, int gap)
{
  int pid = fork();
  if (pid < 0) {
    printf("lockwork: fork failed\n");
    exit(1);
  }

  if (pid == 0) {
    pause(1 + ((wave + slot) % 3));
    lockdemo(hold + (slot % 3) * (hold / 4 + 1));
    pause(1 + ((wave + slot + 1) % 3));
    lockdemo((hold / 2) + (slot % 2) * (hold / 6 + 1));
    pause(gap / 2 + ((wave + slot) % 3));
    exit(0);
  }
}

int
main(int argc, char **argv)
{
  int waves = 5;
  int burst = 3;
  int hold = 120000;
  int gap = 40000;

  if (argc > 1)
    waves = atoi(argv[1]);
  if (argc > 2)
    burst = atoi(argv[2]);
  if (argc > 3)
    hold = atoi(argv[3]);
  if (argc > 4)
    gap = atoi(argv[4]);

  if (waves < 1)
    waves = 1;
  if (waves > 12)
    waves = 12;
  if (burst < 1)
    burst = 1;
  if (burst > 6)
    burst = 6;
  if (hold < 1000)
    hold = 1000;
  if (hold > 1000000)
    hold = 1000000;
  if (gap < 1000)
    gap = 1000;
  if (gap > 200000)
    gap = 200000;

  for (int wave = 0; wave < waves; wave++) {
    for (int slot = 0; slot < burst; slot++)
      spawn_worker(wave, slot, hold, gap);
    pause(1 + (gap / 40000));
  }

  while (wait(0) >= 0)
    ;

  exit(0);
}
