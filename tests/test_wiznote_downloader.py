from tools.wiznote_downloader import WizMigrator


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}

    def post(self, url, data):
        return self.response


class LoginFailureMigrator(WizMigrator):
    def __init__(self):
        super().__init__("user@example.com", "password")
        self.categories_called = False
        self.scan_called = False

    def login(self):
        return False, "需要关闭二次登录验证后重试"

    def get_all_categories(self):
        self.categories_called = True
        return []

    def scan_folder_recursive(self, folder, output_base, all_notes):
        self.scan_called = True


class LoginSuccessMigrator(LoginFailureMigrator):
    def login(self):
        return True, None


def test_run_stops_after_login_failure(capsys):
    migrator = LoginFailureMigrator()

    migrator.run()

    assert not migrator.categories_called
    assert not migrator.scan_called
    assert "开始扫描笔记" not in capsys.readouterr().out


def test_run_continues_after_login_success(capsys):
    migrator = LoginSuccessMigrator()

    migrator.run()

    assert migrator.categories_called
    assert migrator.scan_called
    assert "开始扫描笔记" in capsys.readouterr().out


def test_login_rejects_invalid_api_url():
    migrator = WizMigrator("user@example.com", "password")
    migrator.session = FakeSession(
        FakeResponse(
            {
                "return_code": 200,
                "result": {
                    "token": "token",
                    "kb_guid": "kb-guid",
                    "kapi_url": "None",
                },
            }
        )
    )

    success, error = migrator.login()

    assert not success
    assert "API" in error


def test_login_keeps_default_api_url_when_server_omits_it():
    migrator = WizMigrator("user@example.com", "password")
    migrator.session = FakeSession(
        FakeResponse(
            {
                "return_code": 200,
                "result": {
                    "token": "token",
                    "kb_guid": "kb-guid",
                },
            }
        )
    )

    success, error = migrator.login()

    assert success
    assert error is None
    assert migrator.kapi_url == "https://ks.wiz.cn"
