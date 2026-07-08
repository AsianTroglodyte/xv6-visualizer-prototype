#include "kernel/types.h"
#include "user/user.h"

static void
burn(int ticks)
{
  int deadline = uptime() + ticks;
  volatile int sink = 0;

  while (uptime() < deadline) {
    for (int i = 0; i < 30000; i++)
      sink += i;
  }
}

static void
spawn_child(int wave, int slot, int burn_ticks)
{
  int pid = fork();
  if (pid < 0) {
    printf("schedwork: fork failed\n");
    exit(1);
  }

  if (pid == 0) {
    pause(2 + ((wave + slot) % 3));
    burn(burn_ticks + (slot % 3));
    pause(2 + ((wave + slot + 1) % 3));
    burn((burn_ticks / 2) + 1 + (wave % 2));
    exit(0);
  }
}

int
main(int argc, char **argv)
{
  int waves = 8;
  int burst = 1;
  int burn_ticks = 18;
  int gap = 6;
  int background = 0;

  if (argc > 1)
    waves = atoi(argv[1]);
  if (argc > 2)
    burst = atoi(argv[2]);
  if (argc > 3)
    burn_ticks = atoi(argv[3]);
  if (argc > 4)
    gap = atoi(argv[4]);

  if (waves < 1)
    waves = 1;
  if (waves > 16)
    waves = 16;
  if (burst < 1)
    burst = 1;
  if (burst > 4)
    burst = 4;
  if (burn_ticks < 1)
    burn_ticks = 1;
  if (burn_ticks > 40)
    burn_ticks = 40;
  if (gap < 1)
    gap = 1;
  if (gap > 12)
    gap = 12;

  background = fork();
  if (background < 0) {
    printf("schedwork: background fork failed\n");
    exit(1);
  }
  if (background == 0) {
    burn(waves * (burn_ticks + gap) + 80);
    exit(0);
  }

  for (int wave = 0; wave < waves; wave++) {
    for (int slot = 0; slot < burst; slot++)
      spawn_child(wave, slot, burn_ticks);
    pause(gap + 1);
  }

  while (wait(0) >= 0)
    ;

  exit(0);
}
