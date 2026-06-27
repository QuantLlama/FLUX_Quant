# Order Flow Scalping Strategy Entry Points
# Expose the OrderFlowScalpingStrategy class
class OrderFlowScalpingStrategy:
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
