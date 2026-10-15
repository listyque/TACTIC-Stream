import test_read_parity as read_tests
import test_checkin as checkin_tests


class UploadCheckinParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='upload_checkin_contract', project='admin', name='upload_and_checkin')]

    new_result = checkin_tests.CheckinParity.new_result
