#!/usr/bin/env python3
"""
cache_system.py - Centralized Image Cache System for EXTRACT_PDF
Enhanced cache system with hash collision avoidance and centralized image management
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageCacheSystem:
    """
    Centralized image cache system with hash collision avoidance.
    
    Features:
    - SHA256 + MD5 dual hashing for collision avoidance
    - Centralized image storage under bin folder
    - Metadata tracking with timestamps
    - Automatic deduplication
    - Hash range management
    """
    
    def __init__(self, base_dir: Path = None):
        """Initialize the cache system."""
        if base_dir is None:
            # Default to EXTRACT_IMG_DATA directory (data storage location)
            # This file is now in EXTRACT_IMG_PROJ, but data should go to EXTRACT_IMG_DATA
            script_dir = Path(__file__).parent.parent  # Go up to bin directory
            base_dir = script_dir / "EXTRACT_IMG_DATA"
        
        self.base_dir = base_dir
        # Images and cache file are directly under EXTRACT_IMG_DATA
        self.images_dir = self.base_dir / "images"
        self.cache_file = self.base_dir / "image_cache.json"
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Cache file corrupted, starting fresh")
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to JSON file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _calculate_dual_hash(self, data: bytes) -> Tuple[str, str]:
        """
        Calculate dual hash (SHA256 + MD5) for collision avoidance.
        
        Args:
            data: Image bytes data
            
        Returns:
            Tuple of (sha256_hash, md5_hash)
        """
        sha256_hash = hashlib.sha256(data).hexdigest()
        md5_hash = hashlib.md5(data).hexdigest()
        return sha256_hash, md5_hash
    
    def _get_composite_hash(self, sha256_hash: str, md5_hash: str) -> str:
        """
        Create composite hash for extended collision avoidance.
        
        Format: sha256[:32] + md5[:16] + sha256[32:48]
        Total length: 64 characters
        """
        return sha256_hash[:32] + md5_hash[:16] + sha256_hash[32:48]
    
    def _get_image_filename(self, composite_hash: str) -> str:
        """Generate image filename from composite hash."""
        return f"{composite_hash}.jpg"
    
    def get_cached_description(self, image_data: bytes) -> Optional[str]:
        """
        Get cached description for image data.
        
        Args:
            image_data: Image bytes data
            
        Returns:
            Cached description if exists, None otherwise
        """
        sha256_hash, md5_hash = self._calculate_dual_hash(image_data)
        composite_hash = self._get_composite_hash(sha256_hash, md5_hash)
        
        if composite_hash in self.cache:
            cache_entry = self.cache[composite_hash]
            logger.info(f"Found cached description for image {composite_hash[:12]}...")
            return cache_entry['description']
        
        return None
    
    def store_image_and_description(self, image_data: bytes, description: str, 
                                  source_path: str = None) -> str:
        """
        Store image and its description in cache.
        
        Args:
            image_data: Image bytes data
            description: Image description/analysis
            source_path: Optional source path for reference
            
        Returns:
            Composite hash of the stored image
        """
        sha256_hash, md5_hash = self._calculate_dual_hash(image_data)
        composite_hash = self._get_composite_hash(sha256_hash, md5_hash)
        
        # Store image file
        image_filename = self._get_image_filename(composite_hash)
        image_path = self.images_dir / image_filename
        
        if not image_path.exists():
            try:
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                logger.info(f"Stored new image: {image_filename}")
            except Exception as e:
                logger.error(f"Failed to store image {image_filename}: {e}")
                return composite_hash
        
        # Store cache entry
        self.cache[composite_hash] = {
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'sha256': sha256_hash,
            'md5': md5_hash,
            'image_path': str(image_path),
            'source_path': source_path,
            'file_size': len(image_data)
        }
        
        self._save_cache()
        logger.info(f"Cached description for image {composite_hash[:12]}...")
        return composite_hash
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_images = len(self.cache)
        total_size = sum(entry.get('file_size', 0) for entry in self.cache.values())
        
        return {
            'cache_available': True,
            'total_cached_images': total_images,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.base_dir),
            'images_dir': str(self.images_dir)
        }
    
    def cleanup_orphaned_images(self) -> int:
        """
        Clean up orphaned image files not in cache.
        
        Returns:
            Number of orphaned files removed
        """
        removed_count = 0
        
        if not self.images_dir.exists():
            return removed_count
        
        # Get all cached image filenames
        cached_filenames = set()
        for entry in self.cache.values():
            if 'image_path' in entry:
                cached_filenames.add(Path(entry['image_path']).name)
        
        # Remove orphaned files
        for image_file in self.images_dir.glob('*.jpg'):
            if image_file.name not in cached_filenames:
                try:
                    image_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned image: {image_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned image {image_file.name}: {e}")
        
        return removed_count
    
    def migrate_old_cache(self, old_cache_file: Path) -> int:
        """
        Migrate from old cache format to new system.
        
        Args:
            old_cache_file: Path to old cache file
            
        Returns:
            Number of entries migrated
        """
        if not old_cache_file.exists():
            logger.warning(f"Old cache file not found: {old_cache_file}")
            return 0
        
        try:
            with open(old_cache_file, 'r', encoding='utf-8') as f:
                old_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load old cache: {e}")
            return 0
        
        migrated_count = 0
        
        for old_hash, old_entry in old_cache.items():
            if isinstance(old_entry, dict) and 'description' in old_entry:
                # For old entries, we can't regenerate the exact hash without the image data
                # So we'll store them with their original hash as a fallback
                fallback_hash = f"migrated_{old_hash}"
                
                self.cache[fallback_hash] = {
                    'description': old_entry['description'],
                    'timestamp': old_entry.get('timestamp', datetime.now().isoformat()),
                    'migrated_from': old_hash,
                    'migration_date': datetime.now().isoformat()
                }
                migrated_count += 1
        
        if migrated_count > 0:
            self._save_cache()
            logger.info(f"Migrated {migrated_count} entries from old cache")
        
        return migrated_count
    
    def search_similar_images(self, image_data: bytes, threshold: float = 0.95) -> List[Dict]:
        """
        Search for similar images in cache (placeholder for future implementation).
        
        Args:
            image_data: Image bytes data
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of similar image entries
        """
        # This is a placeholder for future perceptual hashing implementation
        # For now, we only do exact matches
        sha256_hash, md5_hash = self._calculate_dual_hash(image_data)
        composite_hash = self._get_composite_hash(sha256_hash, md5_hash)
        
        if composite_hash in self.cache:
            return [self.cache[composite_hash]]
        
        return []


def main():
    """Command line interface for cache system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="EXTRACT_PDF Cache System")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--cleanup", action="store_true", help="Clean up orphaned images")
    parser.add_argument("--migrate", help="Migrate from old cache file")
    
    args = parser.parse_args()
    
    cache_system = ImageCacheSystem()
    
    if args.stats:
        stats = cache_system.get_cache_stats()
        print("Cache Statistics:")
        print(f"  Total images: {stats['total_images']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Cache directory: {stats['cache_dir']}")
        print(f"  Images directory: {stats['images_dir']}")
    
    if args.cleanup:
        removed = cache_system.cleanup_orphaned_images()
        print(f"Removed {removed} orphaned image files")
    
    if args.migrate:
        migrated = cache_system.migrate_old_cache(Path(args.migrate))
        print(f"Migrated {migrated} entries from old cache")


if __name__ == "__main__":
    main() 