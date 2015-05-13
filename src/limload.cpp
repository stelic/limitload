
#if defined(LINGCC)

#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main (int argc, char *argv[])
{
    const int max_env_size = 16384 - 1;
    const int max_path_size = 4096 - 1;

    // Should be configured at build time.
    char *abs_cmd_path = realpath(argv[0], NULL);
    char *abs_lib_dir_path = dirname(abs_cmd_path);

    char *base_bin_path = getenv("PATH");
    char bin_path[max_env_size + 1];
    snprintf(bin_path, max_env_size,
             "%s/panda3d/bin:%s",
             abs_lib_dir_path, base_bin_path);
    setenv("PATH", bin_path, 1);

    char *base_ld_library_path = getenv("LD_LIBRARY_PATH");
    char ld_library_path[max_env_size + 1];
    snprintf(ld_library_path, max_env_size,
             "%s/panda3d/lib:%s/src/core:%s",
             abs_lib_dir_path, abs_lib_dir_path, base_ld_library_path);
    setenv("LD_LIBRARY_PATH", ld_library_path, 1);

    char *base_python_path = getenv("PYTHONPATH");
    char python_path[max_env_size + 1];
    snprintf(python_path, max_env_size, "%s:%s",
             abs_lib_dir_path, base_python_path);
    setenv("PYTHONPATH", python_path, 1);

    char main_path[max_path_size + 1];
    snprintf(main_path, max_path_size, "%s/src/main.py",
             abs_lib_dir_path);

    char *python_cmd = strdup("python");
    char *opt_unbuff = strdup("-u");

    const int max_num_opt = 1000;
    char **argvm = new char*[max_num_opt];
    int p = 0;
    argvm[p++] = python_cmd;
    argvm[p++] = opt_unbuff;
    argvm[p++] = main_path;
    for (int i = 1; i < argc && p < max_num_opt - 1; ++i) {
        argvm[p++] = argv[i];
    }
    argvm[p++] = NULL;

    execvp(python_cmd, argvm);

    return 0;
}

#elif defined(WINMSVC)

#include <stdio.h>
#include <stdlib.h>
#include <windows.h>

int WINAPI WinMain (HINSTANCE hInstance, HINSTANCE hPrevInstance,
                    LPSTR lpCmdLine, int nCmdShow)
{
    const int max_env_size = 16384 - 1;
    const int max_path_size = 4096 - 1;
    const int max_drive_size = 16 - 1;
    const int max_opt_size = 1024 - 1;
    const int max_cmdline_size = 16384 - 1;
    size_t need_size;

    int argc = __argc;
    char **argv = __argv;

    // Should be configured at build time.
    char *abs_cmd_path = new char[max_path_size + 1];
    _fullpath(abs_cmd_path, argv[0], max_path_size);
    char *drive_letter = new char[max_drive_size + 1];
    char *drive_lib_dir_path = new char[max_path_size + 1];
    _splitpath_s(abs_cmd_path,
                 drive_letter, max_drive_size,
                 drive_lib_dir_path, max_path_size,
                 NULL, 0, NULL, 0);
    char *abs_lib_dir_path = new char[max_path_size];
    _snprintf_s(abs_lib_dir_path, max_path_size, _TRUNCATE, "%s\\%s",
                drive_letter, drive_lib_dir_path);

    char *base_bin_path = new char[max_env_size + 1];
    getenv_s(&need_size, base_bin_path, max_env_size, "PATH");
    char bin_path[max_env_size + 1];
    _snprintf_s(bin_path, max_env_size, _TRUNCATE,
                "%s\\python;%s\\panda3d\\bin;%s\\src\\core;%s",
                abs_lib_dir_path, abs_lib_dir_path, abs_lib_dir_path,
                base_bin_path);
    _putenv_s("PATH", bin_path);

    char *base_python_path = new char[max_env_size + 1];
    getenv_s(&need_size, base_python_path, max_env_size, "PYTHONPATH");
    char *python_path = new char[max_env_size + 1];
    _snprintf_s(python_path, max_env_size, _TRUNCATE, "%s;%s",
                abs_lib_dir_path, base_python_path);
    _putenv_s("PYTHONPATH", python_path);

    char *main_path = new char[max_path_size + 1];
    _snprintf_s(main_path, max_path_size, _TRUNCATE, "%s\\src\\main.py",
                abs_lib_dir_path);

    char *python_cmd = new char[max_path_size + 1];
    _snprintf_s(python_cmd, max_path_size, _TRUNCATE, "pythonw");
    // ...pythonw in order not to show console window.
    char *opt_unbuff = new char[max_opt_size + 1];
    _snprintf_s(opt_unbuff, max_opt_size, _TRUNCATE, "-u");

    char *cmdline = new char[max_cmdline_size + 1];
    _snprintf_s(cmdline, max_cmdline_size, _TRUNCATE, "%s",
                python_cmd);
    _snprintf_s(cmdline, max_cmdline_size, _TRUNCATE, "%s \"%s\"",
                cmdline, opt_unbuff);
    _snprintf_s(cmdline, max_cmdline_size, _TRUNCATE, "%s \"%s\"",
                cmdline, main_path);
    for (int i = 1; i < argc; ++i) {
        _snprintf_s(cmdline, max_cmdline_size, _TRUNCATE, "%s \"%s\"",
                    cmdline, argv[i]);
    }
    //_snprintf_s(cmdline, max_cmdline_size, _TRUNCATE, "calc.exe");
    //printf("{%s}\n", cmdline);

    // system(cmdline);
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcess(NULL, cmdline, NULL, NULL, TRUE, 0, NULL, NULL,
                       &si, &pi)) {
        printf("CreateProcess failed (%d).\n", GetLastError());
        return 1;
    }
    //WaitForSingleObject(pi.hProcess, INFINITE);
    // ...not waiting to avoid the process going into the background.
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return 0;
}

#endif
