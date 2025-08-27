"""
Statistical utility functions for health data analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau, wilcoxon, ttest_rel
from statsmodels.stats.multitest import multipletests
from typing import List, Dict, Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)

class StatisticalValidator:
    """Ensures statistical rigor in all analyses"""

    @staticmethod
    def validate_sample_size(data: Union[List, np.ndarray], min_n: int = 30) -> Dict:
        """Validate if sample size is sufficient for statistical analysis"""
        n = len(data)
        return {
            'sample_size': n,
            'is_sufficient': n >= min_n,
            'min_required': min_n,
            'power_estimate': min(1.0, n / min_n) if n > 0 else 0.0
        }

    @staticmethod
    def check_normality(data: Union[List, np.ndarray], alpha: float = 0.05) -> Dict:
        """Test for normality using multiple methods"""
        data = np.array(data)

        if len(data) < 3:
            return {
                'is_normal': False,
                'reason': 'Insufficient data for normality testing'
            }

        results = {}

        try:
            # Shapiro-Wilk test (best for n < 5000)
            if len(data) <= 5000:
                shapiro_stat, shapiro_p = stats.shapiro(data)
                results['shapiro_wilk'] = {
                    'statistic': float(shapiro_stat),
                    'p_value': float(shapiro_p),
                    'is_normal': shapiro_p > alpha
                }

            # Anderson-Darling test
            anderson_result = stats.anderson(data, dist='norm')
            # Use 5% significance level (index 2)
            anderson_critical = anderson_result.critical_values[2]
            anderson_is_normal = anderson_result.statistic < anderson_critical

            results['anderson_darling'] = {
                'statistic': float(anderson_result.statistic),
                'critical_value': float(anderson_critical),
                'is_normal': anderson_is_normal
            }

            # D'Agostino and Pearson's test
            if len(data) >= 20:
                dagostino_stat, dagostino_p = stats.normaltest(data)
                results['dagostino_pearson'] = {
                    'statistic': float(dagostino_stat),
                    'p_value': float(dagostino_p),
                    'is_normal': dagostino_p > alpha
                }

            # Consensus decision
            normality_tests = [r.get('is_normal', False) for r in results.values()]
            consensus_normal = sum(normality_tests) >= len(normality_tests) / 2

            return {
                'is_normal': consensus_normal,
                'tests': results,
                'consensus': f"{sum(normality_tests)}/{len(normality_tests)} tests indicate normality"
            }

        except Exception as e:
            logger.warning(f"Normality testing failed: {str(e)}")
            return {
                'is_normal': False,
                'reason': f'Testing failed: {str(e)}'
            }

    @staticmethod
    def apply_multiple_testing_correction(p_values: List[float], method: str = 'fdr_bh') -> Dict:
        """Apply correction for multiple hypothesis testing"""
        try:
            corrected_results = multipletests(p_values, method=method)

            return {
                'original_p_values': p_values,
                'corrected_p_values': corrected_results[1].tolist(),
                'rejected_hypotheses': corrected_results[0].tolist(),
                'method': method,
                'alpha_bonferroni': corrected_results[2] if len(corrected_results) > 2 else None
            }
        except Exception as e:
            logger.error(f"Multiple testing correction failed: {str(e)}")
            return {
                'original_p_values': p_values,
                'corrected_p_values': p_values,
                'rejected_hypotheses': [False] * len(p_values),
                'method': 'none',
                'error': str(e)
            }

class EffectSizeCalculator:
    """Calculate various effect size measures"""

    @staticmethod
    def cohens_d(group1: Union[List, np.ndarray], group2: Union[List, np.ndarray]) -> float:
        """Calculate Cohen's d effect size"""
        try:
            group1, group2 = np.array(group1), np.array(group2)
            n1, n2 = len(group1), len(group2)

            if n1 <= 1 or n2 <= 1:
                return 0.0

            # Pooled standard deviation
            pooled_std = np.sqrt(((n1 - 1) * np.var(group1, ddof=1) +
                                 (n2 - 1) * np.var(group2, ddof=1)) / (n1 + n2 - 2))

            if pooled_std == 0:
                return 0.0

            return (np.mean(group1) - np.mean(group2)) / pooled_std

        except Exception as e:
            logger.warning(f"Cohen's d calculation failed: {str(e)}")
            return 0.0

    @staticmethod
    def glass_delta(group1: Union[List, np.ndarray], group2: Union[List, np.ndarray]) -> float:
        """Calculate Glass's delta effect size"""
        try:
            group1, group2 = np.array(group1), np.array(group2)

            std_control = np.std(group2, ddof=1)
            if std_control == 0:
                return 0.0

            return (np.mean(group1) - np.mean(group2)) / std_control

        except Exception as e:
            logger.warning(f"Glass's delta calculation failed: {str(e)}")
            return 0.0

    @staticmethod
    def hedges_g(group1: Union[List, np.ndarray], group2: Union[List, np.ndarray]) -> float:
        """Calculate Hedges' g effect size (bias-corrected Cohen's d)"""
        try:
            cohens_d = EffectSizeCalculator.cohens_d(group1, group2)
            n1, n2 = len(group1), len(group2)

            # Correction factor
            df = n1 + n2 - 2
            correction = 1 - (3 / (4 * df - 1))

            return cohens_d * correction

        except Exception as e:
            logger.warning(f"Hedges' g calculation failed: {str(e)}")
            return 0.0

    @staticmethod
    def interpret_effect_size(effect_size: float, measure: str = 'cohens_d') -> str:
        """Interpret effect size magnitude"""
        abs_effect = abs(effect_size)

        if measure.lower() in ['cohens_d', 'hedges_g']:
            if abs_effect < 0.2:
                return 'negligible'
            elif abs_effect < 0.5:
                return 'small'
            elif abs_effect < 0.8:
                return 'medium'
            else:
                return 'large'

        return 'unknown'

class ConfidenceIntervals:
    """Calculate confidence intervals for various statistics"""

    @staticmethod
    def mean_ci(data: Union[List, np.ndarray], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for mean"""
        try:
            data = np.array(data)
            n = len(data)

            if n <= 1:
                mean_val = np.mean(data)
                return mean_val, mean_val

            mean_val = np.mean(data)
            sem = stats.sem(data)  # Standard error of mean

            # Use t-distribution for small samples
            df = n - 1
            t_value = stats.t.ppf((1 + confidence) / 2, df)

            margin_error = t_value * sem

            return mean_val - margin_error, mean_val + margin_error

        except Exception as e:
            logger.warning(f"Mean CI calculation failed: {str(e)}")
            mean_val = np.mean(data) if len(data) > 0 else 0
            return mean_val, mean_val

    @staticmethod
    def correlation_ci(r: float, n: int, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for correlation coefficient"""
        try:
            if n <= 3 or abs(r) >= 1:
                return r, r

            # Fisher z-transformation
            z = 0.5 * np.log((1 + r) / (1 - r))
            se = 1 / np.sqrt(n - 3)

            alpha = 1 - confidence
            z_critical = stats.norm.ppf(1 - alpha / 2)

            z_lower = z - z_critical * se
            z_upper = z + z_critical * se

            # Transform back
            r_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
            r_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)

            return r_lower, r_upper

        except Exception as e:
            logger.warning(f"Correlation CI calculation failed: {str(e)}")
            return r, r

    @staticmethod
    def proportion_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for proportion (Wilson score interval)"""
        try:
            if n == 0:
                return 0.0, 0.0

            p = successes / n
            alpha = 1 - confidence
            z = stats.norm.ppf(1 - alpha / 2)

            # Wilson score interval
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2 * n)) / denominator
            margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

            return max(0, center - margin), min(1, center + margin)

        except Exception as e:
            logger.warning(f"Proportion CI calculation failed: {str(e)}")
            p = successes / n if n > 0 else 0
            return p, p

class RobustStatistics:
    """Robust statistical measures less sensitive to outliers"""

    @staticmethod
    def median_absolute_deviation(data: Union[List, np.ndarray], scale_factor: float = 1.4826) -> float:
        """Calculate Median Absolute Deviation (MAD)"""
        try:
            data = np.array(data)
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            return mad * scale_factor  # Scale to approximate standard deviation
        except Exception as e:
            logger.warning(f"MAD calculation failed: {str(e)}")
            return 0.0

    @staticmethod
    def modified_z_score(data: Union[List, np.ndarray], value: float) -> float:
        """Calculate modified z-score using MAD"""
        try:
            data = np.array(data)
            median = np.median(data)
            mad = RobustStatistics.median_absolute_deviation(data, scale_factor=1.0)

            if mad == 0:
                return 0.0

            return 0.6745 * (value - median) / mad
        except Exception as e:
            logger.warning(f"Modified z-score calculation failed: {str(e)}")
            return 0.0

    @staticmethod
    def interquartile_range(data: Union[List, np.ndarray]) -> Dict[str, float]:
        """Calculate IQR and related statistics"""
        try:
            data = np.array(data)
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1

            # Outlier bounds
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            return {
                'q1': float(q1),
                'q3': float(q3),
                'iqr': float(iqr),
                'lower_bound': float(lower_bound),
                'upper_bound': float(upper_bound),
                'outliers': data[(data < lower_bound) | (data > upper_bound)].tolist()
            }
        except Exception as e:
            logger.warning(f"IQR calculation failed: {str(e)}")
            return {'q1': 0, 'q3': 0, 'iqr': 0, 'lower_bound': 0, 'upper_bound': 0, 'outliers': []}

    @staticmethod
    def winsorized_mean(data: Union[List, np.ndarray], limits: Tuple[float, float] = (0.05, 0.05)) -> float:
        """Calculate Winsorized mean (limit extreme values)"""
        try:
            from scipy.stats.mstats import winsorize
            winsorized_data = winsorize(data, limits=limits)
            return float(np.mean(winsorized_data))
        except Exception as e:
            logger.warning(f"Winsorized mean calculation failed: {str(e)}")
            return float(np.mean(data)) if len(data) > 0 else 0.0

class StatisticalTests:
    """Collection of statistical tests for health data"""

    @staticmethod
    def paired_comparison(before: Union[List, np.ndarray], after: Union[List, np.ndarray]) -> Dict:
        """Comprehensive paired comparison analysis"""
        try:
            before, after = np.array(before), np.array(after)

            if len(before) != len(after) or len(before) < 2:
                return {'error': 'Invalid data for paired comparison'}

            results = {}

            # Basic statistics
            results['descriptive'] = {
                'before_mean': float(np.mean(before)),
                'after_mean': float(np.mean(after)),
                'mean_difference': float(np.mean(after - before)),
                'before_std': float(np.std(before, ddof=1)),
                'after_std': float(np.std(after, ddof=1))
            }

            # Normality check
            before_normal = StatisticalValidator.check_normality(before)['is_normal']
            after_normal = StatisticalValidator.check_normality(after)['is_normal']
            diff_normal = StatisticalValidator.check_normality(after - before)['is_normal']

            results['normality'] = {
                'before_normal': before_normal,
                'after_normal': after_normal,
                'difference_normal': diff_normal
            }

            # Parametric test (paired t-test)
            if len(before) >= 2:
                t_stat, t_p = ttest_rel(after, before)
                results['t_test'] = {
                    'statistic': float(t_stat),
                    'p_value': float(t_p),
                    'significant': t_p < 0.05
                }

            # Non-parametric test (Wilcoxon signed-rank)
            if len(before) >= 6:  # Minimum for Wilcoxon
                try:
                    w_stat, w_p = wilcoxon(after, before)
                    results['wilcoxon'] = {
                        'statistic': float(w_stat),
                        'p_value': float(w_p),
                        'significant': w_p < 0.05
                    }
                except ValueError as e:
                    results['wilcoxon'] = {'error': str(e)}

            # Effect size
            cohens_d = EffectSizeCalculator.cohens_d(after, before)
            results['effect_size'] = {
                'cohens_d': float(cohens_d),
                'interpretation': EffectSizeCalculator.interpret_effect_size(cohens_d),
                'hedges_g': float(EffectSizeCalculator.hedges_g(after, before))
            }

            # Confidence intervals
            mean_diff = np.mean(after - before)
            ci_lower, ci_upper = ConfidenceIntervals.mean_ci(after - before)
            results['confidence_interval'] = {
                'mean_difference': float(mean_diff),
                'ci_lower': float(ci_lower),
                'ci_upper': float(ci_upper),
                'confidence_level': 0.95
            }

            return results

        except Exception as e:
            logger.error(f"Paired comparison failed: {str(e)}")
            return {'error': str(e)}

    @staticmethod
    def correlation_analysis(x: Union[List, np.ndarray], y: Union[List, np.ndarray]) -> Dict:
        """Comprehensive correlation analysis"""
        try:
            x, y = np.array(x), np.array(y)

            if len(x) != len(y) or len(x) < 3:
                return {'error': 'Invalid data for correlation analysis'}

            results = {}

            # Pearson correlation
            try:
                pearson_r, pearson_p = pearsonr(x, y)
                ci_lower, ci_upper = ConfidenceIntervals.correlation_ci(pearson_r, len(x))

                results['pearson'] = {
                    'correlation': float(pearson_r),
                    'p_value': float(pearson_p),
                    'significant': pearson_p < 0.05,
                    'ci_lower': float(ci_lower),
                    'ci_upper': float(ci_upper)
                }
            except Exception as e:
                results['pearson'] = {'error': str(e)}

            # Spearman correlation
            try:
                spearman_r, spearman_p = spearmanr(x, y)
                results['spearman'] = {
                    'correlation': float(spearman_r),
                    'p_value': float(spearman_p),
                    'significant': spearman_p < 0.05
                }
            except Exception as e:
                results['spearman'] = {'error': str(e)}

            # Kendall's tau
            try:
                kendall_tau, kendall_p = kendalltau(x, y)
                results['kendall'] = {
                    'correlation': float(kendall_tau),
                    'p_value': float(kendall_p),
                    'significant': kendall_p < 0.05
                }
            except Exception as e:
                results['kendall'] = {'error': str(e)}

            return results

        except Exception as e:
            logger.error(f"Correlation analysis failed: {str(e)}")
            return {'error': str(e)}

def format_statistical_summary(analysis_results: Dict) -> str:
    """Format statistical analysis results for human consumption"""
    try:
        summary_parts = []

        if 't_test' in analysis_results:
            t_result = analysis_results['t_test']
            p_val = t_result['p_value']
            significance = "significant" if t_result['significant'] else "not significant"
            summary_parts.append(f"t-test: p={p_val:.3f} ({significance})")

        if 'effect_size' in analysis_results:
            effect = analysis_results['effect_size']
            d_val = effect['cohens_d']
            interpretation = effect['interpretation']
            summary_parts.append(f"Effect size: d={d_val:.3f} ({interpretation})")

        if 'confidence_interval' in analysis_results:
            ci = analysis_results['confidence_interval']
            summary_parts.append(f"95% CI: [{ci['ci_lower']:.3f}, {ci['ci_upper']:.3f}]")

        if 'pearson' in analysis_results:
            pearson = analysis_results['pearson']
            r_val = pearson['correlation']
            significance = "significant" if pearson['significant'] else "not significant"
            summary_parts.append(f"Correlation: r={r_val:.3f} ({significance})")

        return " | ".join(summary_parts) if summary_parts else "No statistical summary available"

    except Exception as e:
        logger.warning(f"Statistical summary formatting failed: {str(e)}")
        return "Statistical summary unavailable"