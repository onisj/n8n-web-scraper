"""
Predictive analytics for content trends and user behavior.

This module provides advanced analytics capabilities for content trends and user behavior.
It includes functionalities for trend prediction, content recommendation, and usage pattern analysis.

Attributes:
    SKLEARN_AVAILABLE (bool): Flag indicating if the scikit-learn library is available.

Note:
    This module requires the scikit-learn library to be installed.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    import pandas as pd
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..config.settings import settings
from ..database.models import ScrapedDocument, SearchQuery

logger = logging.getLogger(__name__)


class TrendPrediction(BaseModel):
    """Trend prediction results."""
    topic: str
    current_popularity: float
    predicted_popularity: float
    trend_direction: str  # 'rising', 'falling', 'stable'
    confidence: float
    time_horizon: int  # days
    factors: List[str]


class ContentRecommendation(BaseModel):
    """Content recommendation."""
    content_id: str
    title: str
    relevance_score: float
    popularity_score: float
    freshness_score: float
    combined_score: float
    reason: str


class UsagePattern(BaseModel):
    """Usage pattern analysis."""
    pattern_type: str
    frequency: float
    peak_hours: List[int]
    popular_topics: List[str]
    user_segments: List[str]
    seasonal_trends: Dict[str, float]


class AnomalyDetection(BaseModel):
    """Anomaly detection results."""
    timestamp: datetime
    metric: str
    value: float
    expected_range: Tuple[float, float]
    anomaly_score: float
    severity: str  # 'low', 'medium', 'high'
    description: str


class PredictiveAnalytics:
    """Predictive analytics engine for content and usage patterns."""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.data_cache = {}
        self._is_initialized = False
        
        # Model configurations
        self.model_configs = {
            'popularity_predictor': {
                'type': 'random_forest',
                'params': {'n_estimators': 100, 'random_state': 42}
            },
            'trend_analyzer': {
                'type': 'linear_regression',
                'params': {}
            },
            'anomaly_detector': {
                'type': 'isolation_forest',
                'params': {'contamination': 0.1, 'random_state': 42}
            }
        }
    
    async def initialize(self) -> None:
        """Initialize predictive models."""
        if self._is_initialized:
            return
            
        if not SKLEARN_AVAILABLE:
            logger.warning("Scikit-learn not available, using basic analytics")
            self._is_initialized = True
            return
        
        try:
            logger.info("Initializing predictive analytics models...")
            
            # Initialize models
            for model_name, config in self.model_configs.items():
                if config['type'] == 'random_forest':
                    self.models[model_name] = RandomForestRegressor(**config['params'])
                elif config['type'] == 'linear_regression':
                    self.models[model_name] = LinearRegression(**config['params'])
                elif config['type'] == 'isolation_forest':
                    self.models[model_name] = IsolationForest(**config['params'])
                
                # Initialize corresponding scaler
                self.scalers[model_name] = StandardScaler()
            
            # Load historical data and train models
            await self._load_and_train_models()
            
            self._is_initialized = True
            logger.info("Predictive analytics models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize predictive models: {e}")
            self._is_initialized = True  # Continue with basic analytics
    
    async def predict_content_trends(self, time_horizon: int = 30) -> List[TrendPrediction]:
        """Predict content trends for the specified time horizon."""
        await self.initialize()
        
        try:
            # Get historical data
            historical_data = await self._get_historical_trends()
            
            if not historical_data:
                return []
            
            predictions = []
            
            for topic, data in historical_data.items():
                prediction = await self._predict_topic_trend(topic, data, time_horizon)
                if prediction:
                    predictions.append(prediction)
            
            # Sort by confidence and predicted popularity
            predictions.sort(key=lambda x: (x.confidence, x.predicted_popularity), reverse=True)
            
            return predictions[:10]  # Top 10 predictions
            
        except Exception as e:
            logger.error(f"Trend prediction failed: {e}")
            return []
    
    async def recommend_content(self, user_context: Dict[str, Any] = None, 
                              limit: int = 10) -> List[ContentRecommendation]:
        """Recommend content based on trends and user context."""
        await self.initialize()
        
        try:
            # Get content metrics
            content_metrics = await self._get_content_metrics()
            
            if not content_metrics:
                return []
            
            recommendations = []
            
            for content_id, metrics in content_metrics.items():
                recommendation = await self._calculate_content_score(
                    content_id, metrics, user_context or {}
                )
                if recommendation:
                    recommendations.append(recommendation)
            
            # Sort by combined score
            recommendations.sort(key=lambda x: x.combined_score, reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Content recommendation failed: {e}")
            return []
    
    async def analyze_usage_patterns(self, days_back: int = 30) -> UsagePattern:
        """Analyze usage patterns from historical data."""
        await self.initialize()
        
        try:
            # Get usage data
            usage_data = await self._get_usage_data(days_back)
            
            if not usage_data:
                return UsagePattern(
                    pattern_type="insufficient_data",
                    frequency=0.0,
                    peak_hours=[],
                    popular_topics=[],
                    user_segments=[],
                    seasonal_trends={}
                )
            
            # Analyze patterns
            pattern_type = self._identify_pattern_type(usage_data)
            frequency = self._calculate_usage_frequency(usage_data)
            peak_hours = self._identify_peak_hours(usage_data)
            popular_topics = self._identify_popular_topics(usage_data)
            user_segments = self._segment_users(usage_data)
            seasonal_trends = self._analyze_seasonal_trends(usage_data)
            
            return UsagePattern(
                pattern_type=pattern_type,
                frequency=frequency,
                peak_hours=peak_hours,
                popular_topics=popular_topics,
                user_segments=user_segments,
                seasonal_trends=seasonal_trends
            )
            
        except Exception as e:
            logger.error(f"Usage pattern analysis failed: {e}")
            return UsagePattern(
                pattern_type="error",
                frequency=0.0,
                peak_hours=[],
                popular_topics=[],
                user_segments=[],
                seasonal_trends={}
            )
    
    async def detect_anomalies(self, metric_type: str = "all") -> List[AnomalyDetection]:
        """Detect anomalies in system metrics."""
        await self.initialize()
        
        try:
            # Get recent metrics
            metrics_data = await self._get_metrics_data()
            
            if not metrics_data:
                return []
            
            anomalies = []
            
            for metric, values in metrics_data.items():
                if metric_type != "all" and metric != metric_type:
                    continue
                
                metric_anomalies = await self._detect_metric_anomalies(metric, values)
                anomalies.extend(metric_anomalies)
            
            # Sort by severity and anomaly score
            severity_order = {'high': 3, 'medium': 2, 'low': 1}
            anomalies.sort(
                key=lambda x: (severity_order.get(x.severity, 0), x.anomaly_score),
                reverse=True
            )
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []
    
    async def _load_and_train_models(self) -> None:
        """Load historical data and train models."""
        try:
            # This would typically load from your database
            # For now, we'll simulate with basic training
            
            # Generate sample training data
            np.random.seed(42)
            n_samples = 1000
            
            # Features: [day_of_week, hour, topic_popularity, content_age, user_activity]
            X = np.random.rand(n_samples, 5)
            
            # Target: content popularity score
            y = (
                X[:, 0] * 0.2 +  # day of week effect
                X[:, 1] * 0.3 +  # hour effect
                X[:, 2] * 0.4 +  # topic popularity
                (1 - X[:, 3]) * 0.1  # newer content is better
            ) + np.random.normal(0, 0.1, n_samples)
            
            # Train popularity predictor
            if 'popularity_predictor' in self.models:
                X_scaled = self.scalers['popularity_predictor'].fit_transform(X)
                self.models['popularity_predictor'].fit(X_scaled, y)
            
            # Train anomaly detector
            if 'anomaly_detector' in self.models:
                # Generate normal and anomalous data
                normal_data = np.random.normal(0, 1, (800, 3))
                anomalous_data = np.random.normal(3, 1, (200, 3))
                anomaly_X = np.vstack([normal_data, anomalous_data])
                
                X_anomaly_scaled = self.scalers['anomaly_detector'].fit_transform(anomaly_X)
                self.models['anomaly_detector'].fit(X_anomaly_scaled)
            
            logger.info("Models trained successfully")
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
    
    async def _get_historical_trends(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical trend data."""
        # This would query your database for historical data
        # For now, return simulated data
        
        topics = ['webhooks', 'workflows', 'nodes', 'api', 'automation']
        historical_data = {}
        
        for topic in topics:
            # Simulate 30 days of data
            data = []
            base_popularity = np.random.uniform(0.3, 0.8)
            
            for i in range(30):
                date = datetime.now() - timedelta(days=30-i)
                # Add some trend and noise
                trend = i * 0.01  # Slight upward trend
                noise = np.random.normal(0, 0.05)
                popularity = max(0, min(1, base_popularity + trend + noise))
                
                data.append({
                    'date': date,
                    'popularity': popularity,
                    'search_count': int(popularity * 100),
                    'view_count': int(popularity * 500)
                })
            
            historical_data[topic] = data
        
        return historical_data
    
    async def _predict_topic_trend(self, topic: str, data: List[Dict[str, Any]], 
                                 time_horizon: int) -> Optional[TrendPrediction]:
        """Predict trend for a specific topic."""
        try:
            if len(data) < 7:  # Need at least a week of data
                return None
            
            # Extract features
            dates = [item['date'] for item in data]
            popularities = [item['popularity'] for item in data]
            
            # Simple linear trend analysis
            X = np.array(range(len(popularities))).reshape(-1, 1)
            y = np.array(popularities)
            
            # Fit linear regression
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict future
            future_X = np.array(range(len(popularities), len(popularities) + time_horizon)).reshape(-1, 1)
            future_predictions = model.predict(future_X)
            
            current_popularity = popularities[-1]
            predicted_popularity = np.mean(future_predictions)
            
            # Determine trend direction
            slope = model.coef_[0]
            if slope > 0.01:
                trend_direction = 'rising'
            elif slope < -0.01:
                trend_direction = 'falling'
            else:
                trend_direction = 'stable'
            
            # Calculate confidence based on R²
            r2 = model.score(X, y)
            confidence = max(0.1, min(1.0, r2))
            
            # Identify factors
            factors = self._identify_trend_factors(topic, data)
            
            return TrendPrediction(
                topic=topic,
                current_popularity=current_popularity,
                predicted_popularity=max(0, min(1, predicted_popularity)),
                trend_direction=trend_direction,
                confidence=confidence,
                time_horizon=time_horizon,
                factors=factors
            )
            
        except Exception as e:
            logger.error(f"Topic trend prediction failed for {topic}: {e}")
            return None
    
    def _identify_trend_factors(self, topic: str, data: List[Dict[str, Any]]) -> List[str]:
        """Identify factors influencing the trend."""
        factors = []
        
        # Analyze recent changes
        recent_data = data[-7:]  # Last week
        older_data = data[-14:-7]  # Previous week
        
        if recent_data and older_data:
            recent_avg = np.mean([item['popularity'] for item in recent_data])
            older_avg = np.mean([item['popularity'] for item in older_data])
            
            if recent_avg > older_avg * 1.1:
                factors.append('increasing_interest')
            elif recent_avg < older_avg * 0.9:
                factors.append('declining_interest')
            
            # Check for volatility
            recent_std = np.std([item['popularity'] for item in recent_data])
            if recent_std > 0.1:
                factors.append('high_volatility')
        
        # Topic-specific factors
        if topic in ['webhooks', 'api']:
            factors.append('integration_demand')
        elif topic in ['workflows', 'automation']:
            factors.append('automation_trend')
        
        return factors
    
    async def _get_content_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get content metrics for recommendation."""
        # This would query your database for content metrics
        # For now, return simulated data
        
        content_metrics = {}
        
        for i in range(50):  # Simulate 50 pieces of content
            content_id = f"content_{i}"
            
            content_metrics[content_id] = {
                'title': f"Content {i}",
                'views': np.random.randint(10, 1000),
                'searches': np.random.randint(1, 100),
                'rating': np.random.uniform(3.0, 5.0),
                'age_days': np.random.randint(1, 365),
                'category': np.random.choice(['nodes', 'workflows', 'api', 'hosting']),
                'complexity': np.random.uniform(0.1, 1.0),
                'last_updated': datetime.now() - timedelta(days=np.random.randint(1, 30))
            }
        
        return content_metrics
    
    async def _calculate_content_score(self, content_id: str, metrics: Dict[str, Any], 
                                     user_context: Dict[str, Any]) -> Optional[ContentRecommendation]:
        """Calculate content recommendation score."""
        try:
            # Relevance score (based on user context)
            relevance_score = self._calculate_relevance_score(metrics, user_context)
            
            # Popularity score
            popularity_score = min(1.0, (metrics['views'] + metrics['searches']) / 1000)
            
            # Freshness score (newer content gets higher score)
            age_days = metrics['age_days']
            freshness_score = max(0.1, 1.0 - (age_days / 365))
            
            # Combined score
            combined_score = (
                relevance_score * 0.4 +
                popularity_score * 0.3 +
                freshness_score * 0.2 +
                (metrics['rating'] / 5.0) * 0.1
            )
            
            # Generate reason
            reason = self._generate_recommendation_reason(metrics, relevance_score, popularity_score)
            
            return ContentRecommendation(
                content_id=content_id,
                title=metrics['title'],
                relevance_score=relevance_score,
                popularity_score=popularity_score,
                freshness_score=freshness_score,
                combined_score=combined_score,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Content score calculation failed for {content_id}: {e}")
            return None
    
    def _calculate_relevance_score(self, metrics: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Calculate relevance score based on user context."""
        score = 0.5  # Base score
        
        # User preferences
        preferred_categories = user_context.get('preferred_categories', [])
        if metrics['category'] in preferred_categories:
            score += 0.3
        
        # User skill level
        user_level = user_context.get('skill_level', 'intermediate')
        content_complexity = metrics['complexity']
        
        if user_level == 'beginner' and content_complexity < 0.4:
            score += 0.2
        elif user_level == 'intermediate' and 0.3 < content_complexity < 0.7:
            score += 0.2
        elif user_level == 'advanced' and content_complexity > 0.6:
            score += 0.2
        
        return min(1.0, score)
    
    def _generate_recommendation_reason(self, metrics: Dict[str, Any], 
                                      relevance_score: float, popularity_score: float) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if popularity_score > 0.7:
            reasons.append("highly popular")
        if relevance_score > 0.7:
            reasons.append("highly relevant")
        if metrics['age_days'] < 30:
            reasons.append("recently updated")
        if metrics['rating'] > 4.5:
            reasons.append("highly rated")
        
        if not reasons:
            return "recommended based on overall score"
        
        return f"Recommended because it's {' and '.join(reasons)}"
    
    async def _get_usage_data(self, days_back: int) -> List[Dict[str, Any]]:
        """Get usage data for pattern analysis."""
        # This would query your database for usage data
        # For now, return simulated data
        
        usage_data = []
        
        for i in range(days_back):
            date = datetime.now() - timedelta(days=days_back-i)
            
            # Simulate hourly data
            for hour in range(24):
                # Peak hours: 9-11 AM and 2-4 PM
                if 9 <= hour <= 11 or 14 <= hour <= 16:
                    base_activity = np.random.uniform(0.7, 1.0)
                else:
                    base_activity = np.random.uniform(0.1, 0.5)
                
                usage_data.append({
                    'timestamp': date.replace(hour=hour),
                    'activity_level': base_activity,
                    'unique_users': int(base_activity * 100),
                    'page_views': int(base_activity * 500),
                    'search_queries': int(base_activity * 50)
                })
        
        return usage_data
    
    def _identify_pattern_type(self, usage_data: List[Dict[str, Any]]) -> str:
        """Identify the type of usage pattern."""
        # Analyze daily patterns
        daily_activity = {}
        for item in usage_data:
            date = item['timestamp'].date()
            if date not in daily_activity:
                daily_activity[date] = []
            daily_activity[date].append(item['activity_level'])
        
        # Calculate daily averages
        daily_averages = [np.mean(activities) for activities in daily_activity.values()]
        
        # Determine pattern
        std_dev = np.std(daily_averages)
        
        if std_dev < 0.1:
            return "steady"
        elif std_dev < 0.2:
            return "moderate_variation"
        else:
            return "high_variation"
    
    def _calculate_usage_frequency(self, usage_data: List[Dict[str, Any]]) -> float:
        """Calculate average usage frequency."""
        if not usage_data:
            return 0.0
        
        total_activity = sum(item['activity_level'] for item in usage_data)
        return total_activity / len(usage_data)
    
    def _identify_peak_hours(self, usage_data: List[Dict[str, Any]]) -> List[int]:
        """Identify peak usage hours."""
        hourly_activity = {}
        
        for item in usage_data:
            hour = item['timestamp'].hour
            if hour not in hourly_activity:
                hourly_activity[hour] = []
            hourly_activity[hour].append(item['activity_level'])
        
        # Calculate average activity per hour
        hourly_averages = {hour: np.mean(activities) for hour, activities in hourly_activity.items()}
        
        # Find hours with above-average activity
        overall_average = np.mean(list(hourly_averages.values()))
        peak_hours = [hour for hour, avg in hourly_averages.items() if avg > overall_average * 1.2]
        
        return sorted(peak_hours)
    
    def _identify_popular_topics(self, usage_data: List[Dict[str, Any]]) -> List[str]:
        """Identify popular topics from usage data."""
        # This would analyze actual search queries and page views
        # For now, return simulated popular topics
        
        topics = ['webhooks', 'workflows', 'nodes', 'api', 'automation', 'hosting']
        # Simulate popularity based on random weights
        weights = np.random.dirichlet(np.ones(len(topics)))
        
        topic_popularity = list(zip(topics, weights))
        topic_popularity.sort(key=lambda x: x[1], reverse=True)
        
        return [topic for topic, _ in topic_popularity[:3]]
    
    def _segment_users(self, usage_data: List[Dict[str, Any]]) -> List[str]:
        """Segment users based on usage patterns."""
        # This would analyze actual user behavior
        # For now, return common user segments
        
        return ['power_users', 'casual_users', 'new_users']
    
    def _analyze_seasonal_trends(self, usage_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze seasonal trends in usage."""
        # Group by day of week
        weekday_activity = {i: [] for i in range(7)}
        
        for item in usage_data:
            weekday = item['timestamp'].weekday()
            weekday_activity[weekday].append(item['activity_level'])
        
        # Calculate averages
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        seasonal_trends = {}
        
        for i, name in enumerate(weekday_names):
            if weekday_activity[i]:
                seasonal_trends[name] = np.mean(weekday_activity[i])
            else:
                seasonal_trends[name] = 0.0
        
        return seasonal_trends
    
    async def _get_metrics_data(self) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get metrics data for anomaly detection."""
        # This would query your monitoring system
        # For now, return simulated metrics
        
        metrics = {}
        
        # Simulate different metrics
        metric_names = ['response_time', 'error_rate', 'cpu_usage', 'memory_usage', 'request_count']
        
        for metric_name in metric_names:
            data = []
            
            # Generate 24 hours of data
            for i in range(24):
                timestamp = datetime.now() - timedelta(hours=24-i)
                
                # Normal values with some noise
                if metric_name == 'response_time':
                    value = np.random.normal(200, 50)  # ms
                elif metric_name == 'error_rate':
                    value = np.random.normal(0.02, 0.01)  # 2% error rate
                elif metric_name == 'cpu_usage':
                    value = np.random.normal(0.6, 0.1)  # 60% CPU
                elif metric_name == 'memory_usage':
                    value = np.random.normal(0.7, 0.1)  # 70% memory
                else:  # request_count
                    value = np.random.normal(1000, 200)  # requests per hour
                
                # Add occasional anomalies
                if np.random.random() < 0.05:  # 5% chance of anomaly
                    if metric_name in ['response_time', 'error_rate']:
                        value *= 3  # Spike
                    else:
                        value *= 1.5
                
                data.append((timestamp, max(0, value)))
            
            metrics[metric_name] = data
        
        return metrics
    
    async def _detect_metric_anomalies(self, metric: str, 
                                     values: List[Tuple[datetime, float]]) -> List[AnomalyDetection]:
        """Detect anomalies in a specific metric."""
        try:
            if len(values) < 10:  # Need sufficient data
                return []
            
            # Extract values and timestamps
            timestamps = [item[0] for item in values]
            metric_values = [item[1] for item in values]
            
            # Calculate statistical bounds
            mean_val = np.mean(metric_values)
            std_val = np.std(metric_values)
            
            # Define normal range (mean ± 2 standard deviations)
            lower_bound = mean_val - 2 * std_val
            upper_bound = mean_val + 2 * std_val
            
            anomalies = []
            
            for timestamp, value in values:
                if value < lower_bound or value > upper_bound:
                    # Calculate anomaly score
                    if value < lower_bound:
                        anomaly_score = (lower_bound - value) / std_val
                    else:
                        anomaly_score = (value - upper_bound) / std_val
                    
                    # Determine severity
                    if anomaly_score > 3:
                        severity = 'high'
                    elif anomaly_score > 2:
                        severity = 'medium'
                    else:
                        severity = 'low'
                    
                    # Generate description
                    if value > upper_bound:
                        description = f"{metric} is unusually high: {value:.2f} (expected: {mean_val:.2f})"
                    else:
                        description = f"{metric} is unusually low: {value:.2f} (expected: {mean_val:.2f})"
                    
                    anomalies.append(AnomalyDetection(
                        timestamp=timestamp,
                        metric=metric,
                        value=value,
                        expected_range=(lower_bound, upper_bound),
                        anomaly_score=anomaly_score,
                        severity=severity,
                        description=description
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed for {metric}: {e}")
            return []


# Factory function
def create_predictive_analytics() -> PredictiveAnalytics:
    """Create and return a predictive analytics instance."""
    return PredictiveAnalytics()