def mocked_popen_init(*args, **kwargs):
    return PopenMocked(*args, **kwargs)


def mocked_restart_popen_init(*args, **kwargs):
    return RestartPopenMocked(*args, **kwargs)


def mocked_remote_popen_init(*args, **kwargs):
    return RemotePopenMocked(*args, **kwargs)


def mocked_remote_popen_init_218(*args, **kwargs):
    return RemotePopenMocked218(*args, **kwargs)


def mocked_popen_init_check_fail(*args, **kwargs):
    return PopenMockedCheckFail(*args, **kwargs)


def mocked_popen_init_cancel_fail(*args, **kwargs):
    return PopenMockedCancelFail(*args, **kwargs)


def mocked_popen_init_forward_fail(*args, **kwargs):
    return PopenMockedForwardFail(*args, **kwargs)


def mocked_popen_init_all_fail(*args, **kwargs):
    return PopenMockedAllFail(*args, **kwargs)


class PopenMocked:
    cmd = ""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def communicate(self):
        return ("stdout".encode("utf-8"), "stderr".encode("utf-8"))

    @property
    def returncode(self):
        return 0


class RestartPopenMocked:
    cmd = ""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def communicate(self):
        return ("stdout".encode("utf-8"), "stderr".encode("utf-8"))

    @property
    def returncode(self):
        if "-O" in self.cmd and "check" in self.cmd:
            return 0
        elif "-O" in self.cmd and "forward" in self.cmd:
            return 0
        elif "-O" in self.cmd and "cancel" in self.cmd:
            return 0
        elif "stop" in self.cmd:
            return 218
        else:
            return 217


class RemotePopenMocked:
    cmd = ""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def communicate(self):
        return ("stdout".encode("utf-8"), "stderr".encode("utf-8"))

    @property
    def returncode(self):
        return 217


class RemotePopenMocked218(RemotePopenMocked):
    @property
    def returncode(self):
        return 218


class PopenMockedCheckFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "check"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "check"]:
            return 255
        else:
            return 0


class PopenMockedCancelFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "cancel"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "cancel"]:
            return 255
        else:
            return 0


class PopenMockedForwardFail(PopenMocked):
    @property
    def returncode(self):
        if self.cmd[5:7] == ["-O", "forward"]:
            return 255
        elif self.cmd[5] == "-v" and self.cmd[6:8] == ["-O", "forward"]:
            return 255
        else:
            return 0


class PopenMockedAllFail(PopenMocked):
    @property
    def returncode(self):
        return 255
