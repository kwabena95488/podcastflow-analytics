{% macro calculate_engagement_score(completion_pct, episode_duration, platform_weight=1.0, skip_count=0, rewind_count=0) %}
    /*
    Calculate engagement score based on multiple factors:
    - Completion percentage (primary factor)
    - Episode duration (longer episodes get bonus for completion)
    - Platform weight (different platforms have different engagement patterns)
    - Skip behavior (negative impact)
    - Rewind behavior (positive impact - indicates interest)
    
    Returns a score between 0-100
    */
    
    case 
        -- High engagement: >80% completion
        when {{ completion_pct }} >= 0.8 then 
            least(100, 
                (90 + 
                 -- Duration bonus: longer episodes get more credit for high completion
                 case when {{ episode_duration }} > 3600 then 10 else 5 end +
                 -- Rewind bonus: indicates re-listening/interest
                 least({{ rewind_count }} * 2, 10) -
                 -- Skip penalty: indicates disengagement
                 least({{ skip_count }} * 3, 15)
                ) * {{ platform_weight }}
            )
            
        -- Medium-high engagement: 50-80% completion
        when {{ completion_pct }} >= 0.5 then 
            least(100,
                (60 + ({{ completion_pct }} - 0.5) * 60 +  -- Scale between 60-78
                 case when {{ episode_duration }} > 3600 then 5 else 2 end +
                 least({{ rewind_count }} * 1.5, 8) -
                 least({{ skip_count }} * 2, 10)
                ) * {{ platform_weight }}
            )
            
        -- Medium engagement: 25-50% completion
        when {{ completion_pct }} >= 0.25 then 
            least(100,
                (30 + ({{ completion_pct }} - 0.25) * 80 +  -- Scale between 30-50
                 case when {{ episode_duration }} > 3600 then 3 else 1 end +
                 least({{ rewind_count }}, 5) -
                 least({{ skip_count }} * 1.5, 8)
                ) * {{ platform_weight }}
            )
            
        -- Low engagement: <25% completion
        else 
            greatest(0,
                ({{ completion_pct }} * 100 +  -- Base score from completion
                 least({{ rewind_count }}, 3) -
                 least({{ skip_count }}, 5)
                ) * {{ platform_weight }}
            )
    end

{% endmacro %} 