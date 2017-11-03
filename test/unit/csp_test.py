from mash.csp import CSP


class TestCSP(object):
    def test_csp_names(self):
        assert CSP.azure == 'azure'
        assert CSP.ec2 == 'ec2'
        assert CSP.gce == 'gce'
