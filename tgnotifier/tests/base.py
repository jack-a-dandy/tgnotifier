import os

def getAbsPath(fname):
	return os.path.dirname(os.path.abspath(__file__)) + '/testdata/' + fname