"""
Medium Harvester Module

Harvests insights from Medium articles.
"""

from typing import Any, Dict, List

from .base_harvester import BaseHarvester


class MediumHarvester(BaseHarvester):
    """Harvester for Medium content"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Medium")
        # TODO: Implement Medium API integration
    
    def harvest(self) -> List[Dict[str, Any]]:
        """Harvest insights from Medium"""
        # TODO: Implement Medium harvesting logic
        self.logger.warning("Medium harvester not yet implemented")
        return []
