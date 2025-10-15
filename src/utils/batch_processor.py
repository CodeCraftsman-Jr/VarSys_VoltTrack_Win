"""
Batch Processor for API Operations
Helps reduce rate limiting by batching operations and adding delays
"""

import time
from typing import List, Callable, Any, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class BatchProcessor:
    """Process operations in batches with rate limiting and progress tracking"""
    
    def __init__(self, batch_size: int = 5, delay_between_batches: float = 2.0, max_workers: int = 3):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_workers = max_workers
        self.progress_callback = None
        self.cancel_event = threading.Event()
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Set callback for progress updates: callback(current, total, message)"""
        self.progress_callback = callback
    
    def cancel(self):
        """Cancel the batch processing"""
        self.cancel_event.set()
    
    def process_batch(self, items: List[Any], operation: Callable[[Any], Dict[str, Any]], 
                     operation_name: str = "Processing") -> Dict[str, Any]:
        """
        Process items in batches with rate limiting
        
        Args:
            items: List of items to process
            operation: Function to call for each item, should return {'success': bool, 'data': Any, 'error': str}
            operation_name: Name for progress reporting
            
        Returns:
            Dict with success count, failed items, and results
        """
        if not items:
            return {'success_count': 0, 'failed_items': [], 'results': []}
        
        total_items = len(items)
        success_count = 0
        failed_items = []
        results = []
        
        # Process in batches
        for batch_start in range(0, total_items, self.batch_size):
            if self.cancel_event.is_set():
                break
                
            batch_end = min(batch_start + self.batch_size, total_items)
            batch_items = items[batch_start:batch_end]
            
            # Update progress
            if self.progress_callback:
                self.progress_callback(
                    batch_start, 
                    total_items, 
                    f"{operation_name} batch {batch_start//self.batch_size + 1} of {(total_items-1)//self.batch_size + 1}"
                )
            
            # Process batch items with limited concurrency
            batch_results = self._process_batch_concurrent(batch_items, operation)
            
            # Collect results
            for i, result in enumerate(batch_results):
                if result['success']:
                    success_count += 1
                    results.append(result.get('data'))
                else:
                    failed_items.append({
                        'item': batch_items[i],
                        'error': result.get('error', 'Unknown error')
                    })
            
            # Delay between batches (except for the last batch)
            if batch_end < total_items and not self.cancel_event.is_set():
                time.sleep(self.delay_between_batches)
        
        return {
            'success_count': success_count,
            'failed_items': failed_items,
            'results': results,
            'cancelled': self.cancel_event.is_set()
        }
    
    def _process_batch_concurrent(self, batch_items: List[Any], operation: Callable[[Any], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a single batch with limited concurrency"""
        results = [None] * len(batch_items)
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch_items))) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(operation, item): i 
                for i, item in enumerate(batch_items)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                if self.cancel_event.is_set():
                    break
                    
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    results[index] = {
                        'success': False,
                        'error': f'Exception during processing: {str(e)}'
                    }
        
        # Fill any None results (from cancellation)
        for i, result in enumerate(results):
            if result is None:
                results[i] = {
                    'success': False,
                    'error': 'Operation was cancelled'
                }
        
        return results

class SyncBatchProcessor(BatchProcessor):
    """Specialized batch processor for sync operations"""
    
    def __init__(self):
        # More conservative settings for sync operations
        super().__init__(
            batch_size=3,  # Smaller batches for sync
            delay_between_batches=3.0,  # Longer delays
            max_workers=2  # Less concurrency
        )
    
    def sync_meters(self, meters: List[Dict], sync_function: Callable) -> Dict[str, Any]:
        """Sync meters with progress tracking"""
        def meter_operation(meter):
            try:
                result = sync_function(
                    meter_id=meter.get('$id', meter.get('id')),  # Handle both formats
                    home_name=meter['home_name'],
                    meter_name=meter['meter_name'],
                    meter_type=meter.get('meter_type', meter.get('meter_type_fixed', 'electricity')),
                    user_id=meter['user_id'],
                    created_at=meter.get('created_at')
                )
                return {'success': True, 'data': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return self.process_batch(meters, meter_operation, "Syncing meters")
    
    def sync_readings(self, readings: List[Dict], sync_function: Callable) -> Dict[str, Any]:
        """Sync readings with progress tracking"""
        def reading_operation(reading):
            try:
                result = sync_function(
                    reading_id=reading.get('$id', reading.get('id')),  # Handle both formats
                    meter_id=reading['meter_id'],
                    reading_value=reading['reading_value'],
                    reading_date=reading['reading_date'],
                    user_id=reading['user_id'],
                    created_at=reading.get('created_at')
                )
                return {'success': True, 'data': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return self.process_batch(readings, reading_operation, "Syncing readings")
