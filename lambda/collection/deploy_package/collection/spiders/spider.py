class Spider:
    def __init__(self, name, domain):
        self.name = name
        self.domain = domain

    def getName(self):
        return self.name

    def getDomain(self):
        return self.domain

    def setPipeline(self, DatasetPipeline):
        self.pipeline = DatasetPipeline

    def start(self, start):
        pass

    def log(self, message):
        print(f"[{self.name}] LOG: {message}")
