from enum import Enum

class TimeSlot(Enum):
    """Enumeration of possible time slots for sessions across 5 days."""
    # Day 1 (Monday)
    D1H8_10 = "d1h8-10"  # Monday 8:00-10:00
    D1H10_12 = "d1h10-12"  # Monday 10:00-12:00
    D1H14_16 = "d1h14-16"  # Monday 14:00-16:00
    
    # Day 2 (Tuesday)
    D2H8_10 = "d2h8-10"  # Tuesday 8:00-10:00
    D2H10_12 = "d2h10-12"  # Tuesday 10:00-12:00
    D2H14_16 = "d2h14-16"  # Tuesday 14:00-16:00
    
    # Day 3 (Wednesday)
    D3H8_10 = "d3h8-10"  # Wednesday 8:00-10:00
    D3H10_12 = "d3h10-12"  # Wednesday 10:00-12:00
    D3H14_16 = "d3h14-16"  # Wednesday 14:00-16:00
    
    # Day 4 (Thursday)
    D4H8_10 = "d4h8-10"  # Thursday 8:00-10:00
    D4H10_12 = "d4h10-12"  # Thursday 10:00-12:00
    D4H14_16 = "d4h14-16"  # Thursday 14:00-16:00
    
    # Day 5 (Friday)
    D5H8_10 = "d5h8-10"  # Friday 8:00-10:00
    D5H10_12 = "d5h10-12"  # Friday 10:00-12:00
    D5H14_16 = "d5h14-16"  # Friday 14:00-16:00

    @classmethod
    def get_time_slot(cls, day: int, start_hour: int) -> 'TimeSlot':
        """Get the time slot enum value based on day and start hour."""
        if not 1 <= day <= 5:
            raise ValueError("Day must be between 1 and 5")
        if start_hour not in [8, 10, 14]:
            raise ValueError("Start hour must be 8, 10, or 14")
        
        hour_suffix = f"h{start_hour}-{start_hour + 2}"
        return cls[f"D{day}{hour_suffix}"]

    @classmethod
    def get_all_slots(cls) -> list[str]:
        """Get all possible time slot values as strings."""
        return [slot.value for slot in cls] 