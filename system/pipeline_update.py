"""
Pipeline Update Script - Switch to Cost-Optimized Analyzer
=========================================================

This script updates the pipeline to use the new cost-optimized method.
"""

import re

def update_pipeline_file():
    """Update the pipeline to use cost-optimized analyzer"""
    
    pipeline_file = "/home/user/webapp/system/real_tervyx_pipeline.py"
    
    # Read current file
    with open(pipeline_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the analyze_batch call with process_batch_optimized
    old_pattern = r'analyses = await self\.ai_analyzer\.analyze_batch\(\s*papers=papers,\s*substance=substance,\s*outcome_category=outcome_category\s*\)'
    
    new_call = '''analyses = await self.ai_analyzer.process_batch_optimized(
                papers=papers,
                substance=substance,
                outcome_category=outcome_category,
                relevance_threshold=0.6,  # Filter out irrelevant papers
                confidence_threshold=0.7  # Retry with Pro if confidence too low
            )'''
    
    # Update the call
    content_updated = re.sub(old_pattern, new_call, content, flags=re.DOTALL)
    
    # Also update the metadata to reflect cost optimization
    metadata_pattern = r"'ai_analysis': 'Gemini 1\.5 Flash'"
    metadata_replacement = "'ai_analysis': 'Gemini Tiered (Flash-Lite + Flash + Pro)'"
    
    content_updated = re.sub(metadata_pattern, metadata_replacement, content_updated)
    
    # Write updated file
    with open(pipeline_file, 'w', encoding='utf-8') as f:
        f.write(content_updated)
    
    print("✅ Updated pipeline to use cost-optimized analyzer")
    print("🔧 Changes made:")
    print("  - analyze_batch → process_batch_optimized")
    print("  - Added relevance_threshold=0.6")
    print("  - Added confidence_threshold=0.7") 
    print("  - Updated AI analysis metadata")

if __name__ == "__main__":
    update_pipeline_file()