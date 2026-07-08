#include "kernel/types.h"
#include "kernel/fcntl.h"
#include "kernel/riscv.h"
#include "user/user.h"

static void
write_all(int fd, char *s)
{
  int n = strlen(s);
  if (write(fd, s, n) != n) {
    printf("vizwork: write failed\n");
    exit(1);
  }
}

static void
run_wave(int wave, int delay)
{
  int p[2];
  char *argv[] = {"sh", 0};

  if (pipe(p) < 0) {
    printf("vizwork: pipe failed\n");
    exit(1);
  }

  int pid = fork();
  if (pid < 0) {
    printf("vizwork: fork failed\n");
    exit(1);
  }

  if (pid == 0) {
    close(0);
    dup(p[0]);
    close(p[0]);
    close(p[1]);
    exec("sh", argv);
    printf("vizwork: exec sh failed\n");
    exit(1);
  }

  close(p[0]);

  if (wave % 2 == 0) {
    write_all(p[1], "echo wave0 &\n");
    write_all(p[1], "sleepy 50\n");
    write_all(p[1], "ls &\n");
    write_all(p[1], "sleepy 50\n");
    write_all(p[1], "wc README &\n");
    write_all(p[1], "sleepy 50\n");
  } else {
    write_all(p[1], "echo wave1 &\n");
    write_all(p[1], "sleepy 50\n");
    write_all(p[1], "cat README &\n");
    write_all(p[1], "sleepy 50\n");
    write_all(p[1], "wc README &\n");
    write_all(p[1], "sleepy 50\n");
  }

  close(p[1]);
  wait(0);
  pause(delay);
}

int
main(int argc, char **argv)
{
  int waves = 4;
  int delay = 15;

  if (argc > 1)
    waves = atoi(argv[1]);
  if (argc > 2)
    delay = atoi(argv[2]);

  if (waves < 1)
    waves = 1;
  if (waves > 12)
    waves = 12;
  if (delay < 1)
    delay = 1;

  for (int wave = 0; wave < waves; wave++) {
    run_wave(wave, delay);
  }

  exit(0);
}
