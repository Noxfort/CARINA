#!/usr/bin/env python3
"""
Test script for the PeriodicDataCollector class
"""

import sys
import os
import time

# Add src to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sds.periodic_data_collector import PeriodicDataCollector

def test_basic_functionality():
    """Test basic functionality of PeriodicDataCollector"""
    print("Testing PeriodicDataCollector basic functionality...")
    
    # Create collector with 2 second update interval
    collector = PeriodicDataCollector(update_interval=2.0)
    
    # Use a base timestamp to simulate realistic timing
    base_timestamp = 1000.0
    
    # Add some sample data
    edge_data = {
        'edge_1': {'occupancy': 0.5, 'speed': 10.0, 'queue': 3.0},
        'edge_2': {'occupancy': 0.8, 'speed': 5.0, 'queue': 8.0}
    }
    
    collector.add_sample(base_timestamp, edge_data)
    
    # Check that no update is generated before interval
    payload = collector.compute_aggregated_payload(base_timestamp + 1.0, {})
    assert payload is None, "Should not generate payload before interval"
    print("✓ Correctly withheld update before interval")
    
    # Check that update is generated after interval
    payload = collector.compute_aggregated_payload(base_timestamp + 3.0, {'agent_1': 'ADULT'})
    assert payload is not None, "Should generate payload after interval"
    assert 'edges' in payload, "Payload should contain edges"
    assert 'maturity' in payload, "Payload should contain maturity"
    assert payload['maturity']['agent_1'] == 'ADULT', "Maturity data should be preserved"
    print("✓ Correctly generated payload after interval")
    
    # Check edge data
    edges = payload['edges']
    assert 'edge_1' in edges, "Edge 1 should be in payload"
    assert 'edge_2' in edges, "Edge 2 should be in payload"
    
    edge1_data = edges['edge_1']
    assert 'congestion' in edge1_data, "Edge data should contain congestion"
    assert 'speed' in edge1_data, "Edge data should contain speed"
    assert 'vehicles' in edge1_data, "Edge data should contain vehicles"
    print("✓ Edge data structure is correct")
    
    print("All basic functionality tests passed!")

def test_data_aggregation():
    """Test data aggregation over time"""
    print("\nTesting data aggregation...")
    
    collector = PeriodicDataCollector(update_interval=1.0)
    
    # Use a base timestamp
    base_time = 1000.0
    
    # Add multiple samples for the same edge
    # Add low congestion sample
    collector.add_sample(base_time, {
        'edge_1': {'occupancy': 0.1, 'speed': 15.0, 'queue': 1.0}
    })
    
    # Add high congestion sample
    collector.add_sample(base_time + 0.5, {
        'edge_1': {'occupancy': 0.9, 'speed': 2.0, 'queue': 15.0}
    })
    
    # Generate payload
    payload = collector.compute_aggregated_payload(base_time + 2.0, {})
    
    assert payload is not None, "Should generate payload"
    
    edge_data = payload['edges']['edge_1']
    congestion = edge_data['congestion']
    
    # Should be somewhere between 10% and 90% (averaged)
    assert 10.0 <= congestion <= 90.0, f"Congestion {congestion}% should be between 10% and 90%"
    print(f"✓ Aggregated congestion is reasonable: {congestion:.1f}%")
    
    print("Data aggregation tests passed!")

def test_edge_grouping():
    """Test edge grouping for bidirectional roads"""
    print("\nTesting edge grouping...")
    
    collector = PeriodicDataCollector(update_interval=1.0)
    base_time = 1000.0
    
    # Add data for bidirectional edges
    collector.add_sample(base_time, {
        '123': {'occupancy': 0.5, 'speed': 10.0, 'queue': 5.0},
        '-123': {'occupancy': 0.6, 'speed': 8.0, 'queue': 6.0}
    })
    
    payload = collector.compute_aggregated_payload(base_time + 2.0, {})
    
    assert payload is not None, "Should generate payload"
    
    edges = payload['edges']
    assert '123' in edges, "Original edge should be present"
    assert '-123' in edges, "Negative edge should be present"
    
    # Both edges should have similar congestion (grouped and averaged)
    congestion_123 = edges['123']['congestion']
    congestion_neg123 = edges['-123']['congestion']
    
    # Should be close to each other (both representing the same road)
    diff = abs(congestion_123 - congestion_neg123)
    assert diff < 10.0, f"Bidirectional edges should have similar congestion, got {congestion_123:.1f}% and {congestion_neg123:.1f}%"
    print(f"✓ Bidirectional edges have similar congestion: {congestion_123:.1f}% and {congestion_neg123:.1f}%")
    
    print("Edge grouping tests passed!")

if __name__ == "__main__":
    print("Running PeriodicDataCollector tests...\n")
    
    try:
        test_basic_functionality()
        test_data_aggregation()
        test_edge_grouping()
        
        print("\n🎉 All tests passed! PeriodicDataCollector is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)