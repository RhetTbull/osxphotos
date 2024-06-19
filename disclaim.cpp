#include <stdio.h>
#include <stdlib.h>
#include <spawn.h>
#include <signal.h>
#include <string.h>
#include <unistd.h>

extern "C" {
int responsibility_spawnattrs_setdisclaim(posix_spawnattr_t attrs, int disclaim)
__attribute__((availability(macos,introduced=10.14),weak_import));
char ***_NSGetArgv();
}

#define CHECK_SPAWN(expr) \
    if (int err = (expr)) { \
        posix_spawnattr_destroy(&attr); \
        fprintf(stderr, "[disclaim] %s: %s", #expr, strerror(err)); \
        exit(err); \
    }

/*
    Re-launches the process with disclaimed responsibilities,
    effectively making it responsible for its own permissions.

    Based on https://www.qt.io/blog/the-curious-case-of-the-responsible-process
*/
extern "C" void disclaim()
{
    posix_spawnattr_t attr;
    CHECK_SPAWN(posix_spawnattr_init(&attr));

    // Behave as exec
    short flags = POSIX_SPAWN_SETEXEC;

    // Reset signal mask
    sigset_t no_signals;
    sigemptyset(&no_signals);
    CHECK_SPAWN(posix_spawnattr_setsigmask(&attr, &no_signals));
    flags |= POSIX_SPAWN_SETSIGMASK;

    // Reset all signals to their default handlers
    sigset_t all_signals;
    sigfillset(&all_signals);
    CHECK_SPAWN(posix_spawnattr_setsigdefault(&attr, &all_signals));
    flags |= POSIX_SPAWN_SETSIGDEF;

    CHECK_SPAWN(posix_spawnattr_setflags(&attr, flags));

    if (__builtin_available(macOS 10.14, *)) {
        // Disclaim TCC responsibilities for parent, making
        // the launched process the responsible process.
        if (responsibility_spawnattrs_setdisclaim)
            CHECK_SPAWN(responsibility_spawnattrs_setdisclaim(&attr, 1));
    }

    pid_t pid = 0;
    char **argv = *_NSGetArgv();
    extern char **environ;
    CHECK_SPAWN(posix_spawnp(&pid, argv[0], nullptr, &attr, argv, environ));
}
