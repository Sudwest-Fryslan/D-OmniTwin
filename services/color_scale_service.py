"""
Visualisatie Color Service
===========================
Genereert kleuren op basis van database color schemas en classification methods.
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text


class ColorScaleService:
    """Service voor het genereren van kleuren op basis van visualisatie schema's"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def interpolate_color(self, color1: str, color2: str, t: float) -> str:
        """Interpoleer tussen twee hex kleuren"""
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)
        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)
        
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def generate_color_ramp(self, colors: Dict[str, str], num_classes: int) -> List[str]:
        """Genereer color ramp van min → mid → max"""
        min_color = colors["min"]
        mid_color = colors["mid"]
        max_color = colors["max"]
        
        ramp = []
        # First half: min → mid
        for i in range(num_classes // 2):
            t = i / (num_classes // 2)
            ramp.append(self.interpolate_color(min_color, mid_color, t))
        
        # Second half: mid → max
        for i in range(num_classes - len(ramp)):
            t = i / (num_classes - len(ramp))
            ramp.append(self.interpolate_color(mid_color, max_color, t))
        
        return ramp
    
    def classify_quantile(self, values: List[float], num_classes: int) -> List[float]:
        """Quantile classificatie (gelijke aantallen per klasse)"""
        if len(values) < num_classes:
            return []
        
        percentiles = np.linspace(0, 100, num_classes + 1)[1:-1]
        return [float(np.percentile(values, p)) for p in percentiles]
    
    def classify_equal_interval(self, values: List[float], num_classes: int) -> List[float]:
        """Equal interval classificatie"""
        min_val = min(values)
        max_val = max(values)
        interval = (max_val - min_val) / num_classes
        
        return [min_val + interval * i for i in range(1, num_classes)]
    
    def classify_jenks(self, values: List[float], num_classes: int) -> List[float]:
        """
        Natural Breaks (Jenks) classificatie.
        Simplified implementation - uses quantile as approximation for now.
        """
        # TODO: Implement proper Jenks algorithm
        # For now, fallback to quantile
        return self.classify_quantile(values, num_classes)
    
    def classify_diverging_midpoint(
        self, 
        values: List[float], 
        num_classes: int,
        midpoint: Optional[float] = None
    ) -> List[float]:
        """
        Diverging classification met midpoint (bijv. 50 voor index scores).
        """
        if midpoint is None:
            midpoint = np.median(values)
        
        # Split in twee helften
        below = [v for v in values if v < midpoint]
        above = [v for v in values if v >= midpoint]
        
        half_classes = num_classes // 2
        breaks = []
        
        # Below midpoint breaks
        if len(below) > 0:
            below_breaks = self.classify_quantile(below, half_classes)
            breaks.extend(below_breaks)
        
        # Midpoint
        breaks.append(midpoint)
        
        # Above midpoint breaks
        if len(above) > 0:
            above_breaks = self.classify_quantile(above, half_classes)
            breaks.extend(above_breaks)
        
        return breaks
    
    def get_color_for_value(
        self,
        value: float,
        color_ramp: List[str],
        breaks: List[float],
        nodata_color: str = "#d1d5db"
    ) -> str:
        """Map een waarde naar een kleur"""
        if value is None:
            return nodata_color
        
        # Find which class the value belongs to
        class_index = 0
        for i, threshold in enumerate(breaks):
            if value >= threshold:
                class_index = i + 1
        
        # Clamp to available colors
        class_index = min(class_index, len(color_ramp) - 1)
        
        return color_ramp[class_index]
    
    def get_visualization_config(self, indicator_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Haal visualisatie configuratie op voor indicator.
        Returns color schema + classification method.
        """
        try:
            query = text("""
                SELECT 
                    cs.id as schema_id,
                    cs.naam as schema_naam,
                    cs.colors,
                    cs.palette_type,
                    cs.classificatie,
                    cs.klassen,
                    cs.nodata_kleur,
                    i.score_type
                FROM indicatoren i
                LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id
                WHERE i.uuid::text = :indicator_uuid AND i.color_schema_id IS NOT NULL
            """)
            
            result = self.db.execute(query, {"indicator_uuid": indicator_uuid}).fetchone()
            
            if result:
                return dict(result._mapping)
            
            # Fallback to profile matching
            profile_query = text("""
                SELECT 
                    cs.id as schema_id,
                    cs.naam as schema_naam,
                    cs.colors,
                    cs.palette_type,
                    COALESCE(vp.classificatie_override, cs.classificatie) as classificatie,
                    COALESCE(vp.klassen_override, cs.klassen) as klassen,
                    cs.nodata_kleur,
                    vp.midpoint_waarde,
                    i.score_type
                FROM indicatoren i
                LEFT JOIN visualisatie_profielen vp 
                    ON i.naam LIKE vp.indicator_pattern AND vp.is_actief = true
                LEFT JOIN color_schemas cs ON vp.color_schema_id = cs.id
                WHERE i.uuid::text = :indicator_uuid AND cs.id IS NOT NULL
                ORDER BY vp.id ASC
                LIMIT 1
            """)
            
            result = self.db.execute(profile_query, {"indicator_uuid": indicator_uuid}).fetchone()
            
            if result:
                return dict(result._mapping)
            
            return None
            
        except Exception as e:
            from services.logging_service import AppLogger
            AppLogger.error(f"get_visualization_config failed: {e}", category="KAART")
            return None
    
    def compute_colors_for_data(
        self,
        values: List[float],
        indicator_uuid: str
    ) -> Tuple[List[str], List[float], str]:
        """
        Compute color ramp and breaks for given data values.
        
        Returns:
            (color_ramp, breaks, nodata_color)
        """
        config = self.get_visualization_config(indicator_uuid)
        
        if not config:
            # Fallback to default
            color_ramp = ["#ef4444", "#f87171", "#fb923c", "#fbbf24", "#a3e635", "#4ade80", "#10b981"]
            num_classes = 7
            nodata_color = "#d1d5db"
            classificatie = "quantile"
            score_type = "+/+"
        else:
            colors = config["colors"]
            num_classes = config["klassen"]
            nodata_color = config["nodata_kleur"]
            classificatie = config["classificatie"]
            score_type = config.get("score_type", "+/+")
            
            color_ramp = self.generate_color_ramp(colors, num_classes)
        
        # 🔄 SCORE TYPE INVERSION LOGIC
        # +/+ : High value = Good → normal (low=red/blue, high=green/red)
        # +/- : High value = Bad → REVERSE colors
        # -/+ : Low value = Good → REVERSE colors  
        # -/- : Low value = Bad → normal
        should_reverse = score_type in ['+/-', '-/+']
        if should_reverse:
            color_ramp = list(reversed(color_ramp))
        
        # Compute breaks based on classification method
        if len(values) < num_classes:
            breaks = []
        elif classificatie == "quantile":
            breaks = self.classify_quantile(values, num_classes)
        elif classificatie == "equal_interval":
            breaks = self.classify_equal_interval(values, num_classes)
        elif classificatie == "jenks":
            breaks = self.classify_jenks(values, num_classes)
        elif classificatie == "diverging_midpoint":
            midpoint = config.get("midpoint_waarde") if config else None
            breaks = self.classify_diverging_midpoint(values, num_classes, midpoint)
        else:
            breaks = self.classify_quantile(values, num_classes)
        
        return color_ramp, breaks, nodata_color
