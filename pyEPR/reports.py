"""
Module for reporting utility functions

@author: Zlatko K Minev
"""

import numpy as np
import pandas as pd

from .toolbox.plotting import legend_translucent, plt


def _style_plot_convergence(
    ax, ylabel=None, xlabel="Pass number", ylabel_col="k", y_title=False
):
    ax.set_xlabel(xlabel)
    if ylabel:
        if y_title:
            ax.set_title(ylabel)
        else:
            ax.set_ylabel(ylabel, color=ylabel_col)
    ax.grid()
    ax.autoscale(tight=False)
    ax.set_axisbelow(True)  # Don't allow the axis to be on top of your data
    ax.minorticks_on()
    ax.grid(which="minor", linestyle=":", linewidth="0.5", color="black", alpha=0.2)
    ax.grid(which="major", alpha=0.5)


_style_plot_conv_kw = dict(marker="o", ms=4)


def plot_convergence_max_df(ax, s, kw={}, color="r"):
    """For a single pass"""
    s.plot(ax=ax, **{**dict(c="r"), **_style_plot_conv_kw, **kw})
    ax.set_yscale("log")
    _style_plot_convergence(ax)
    fig = ax.figure
    fig.text(0.45, 0.95, s.name, ha="center", va="bottom", size="medium", color=color)
    ax.tick_params(axis="y", labelcolor=color)
    # ax.axhline(1.0, color='k', lw=1.5,alpha= 0.35)
    # ax.axhline(0.1, color='k', lw=1.5,alpha= 0.35)
    ax.grid(which="minor", linestyle=":", linewidth="0.5", color=color, alpha=0.25)
    ax.grid(which="major", color="#c4abab", alpha=0.5)
    ax.spines["left"].set_color(color)


def plot_convergence_solved_elem(ax, s, kw={}, color="b"):
    """For a single pass"""
    (s / 1000).plot(ax=ax, **{**dict(c="b"), **_style_plot_conv_kw, **kw})
    _style_plot_convergence(ax)
    # ax.set_ylim([100,None])
    # ax.set_yscale("log")
    ax.minorticks_off()
    ax.grid(False)
    ax.tick_params(axis="y", labelcolor=color)
    # ax.ticklabel_format(style='sci',scilimits=(0,0))
    fig = ax.figure
    fig.text(
        0.6,
        0.95,
        "Solved elements (1000s)",
        ha="center",
        va="bottom",
        size="medium",
        color=color,
    )
    ax.spines["left"].set_color("r")
    ax.spines["right"].set_color(color)


def plot_convergence_f_vspass(ax, s, kw={}):
    """For a single pass"""
    if s is not None:
        (s).plot(ax=ax, **{**_style_plot_conv_kw, **kw})
        _style_plot_convergence(ax, "Eigenmode f vs. pass [GHz]", y_title=True)
        legend_translucent(ax, leg_kw=dict(fontsize=6))


def plot_convergence_maxdf_vs_sol(ax, s, s2, kw={}):
    """
    ax, 'Max Δf %', 'Solved elements', kw for plot
    """
    s = s.copy()
    s.index = s2
    (s).plot(ax=ax, **{**_style_plot_conv_kw, **kw})
    _style_plot_convergence(ax, s.name, xlabel="Solved elements", y_title=True)
    ax.set_yscale("log")
    ax.set_xscale("log")


# quick and dirty use
def _plot_q3d_convergence_main(epr, RES):
    """
    Plot alpha and frequency convergence for Q3D LOM analysis.
    
    Args:
        epr: DistributedAnalysis object (not used for Q3D, kept for API compatibility)
        RES: DataFrame with 'alpha' and 'fQ' columns from LOM analysis
    """
    # Create our own figure instead of relying on HFSS convergence report
    fig, ax = plt.subplots(figsize=(8, 4))
    ax2 = ax.twinx()
    
    # IMPORTANT: Make twin axis background transparent so it doesn't cover the primary axis
    ax2.set_frame_on(True)
    ax2.patch.set_visible(False)
    # Ensure primary axis is drawn on top
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)  # Make primary axis background transparent too
    fig.patch.set_visible(True)  # But keep figure background visible
    
    # Handle case where RES might have only one row
    if len(RES) == 0:
        ax.text(0.5, 0.5, 'No data to plot', ha='center', va='center', transform=ax.transAxes)
        return fig
    
    # Get x-axis values (pass numbers)
    x_values = np.array(RES.index.values, dtype=float)
    
    # Plot alpha (blue, left axis) and frequency (red, right axis)
    # Convert to numeric arrays, handling potential list/object types
    def to_numeric_array(series):
        """Convert series to numeric array, extracting first element if values are lists."""
        values = []
        for v in series:
            if isinstance(v, (list, np.ndarray)):
                # Take first element if it's a list/array
                values.append(float(v[0]) if len(v) > 0 else np.nan)
            elif v is None:
                values.append(np.nan)
            else:
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    values.append(np.nan)
        return np.array(values, dtype=float)
    
    alpha_data = to_numeric_array(RES["alpha"])
    freq_data = to_numeric_array(RES["fQ"]) * 1000  # Convert to MHz
    
    # Debug: print the data to diagnose plotting issues
    print(f"DEBUG plot_convergence: x_values = {x_values}")
    print(f"DEBUG plot_convergence: alpha_data = {alpha_data}")
    print(f"DEBUG plot_convergence: freq_data = {freq_data}")
    
    # Filter out NaN and inf values
    alpha_valid_mask = np.isfinite(alpha_data)
    freq_valid_mask = np.isfinite(freq_data)
    
    print(f"DEBUG plot_convergence: alpha_valid_mask = {alpha_valid_mask} (sum={np.sum(alpha_valid_mask)})")
    print(f"DEBUG plot_convergence: freq_valid_mask = {freq_valid_mask} (sum={np.sum(freq_valid_mask)})")
    
    # Plot with explicit arrays to ensure visibility
    # Use zorder to ensure lines are visible above grid
    if np.any(alpha_valid_mask):
        line_alpha, = ax.plot(x_values[alpha_valid_mask], alpha_data[alpha_valid_mask], 
                c="b", marker='o', ms=6, lw=1.5, label='Alpha', zorder=10)
        print(f"DEBUG: Alpha line created: {line_alpha}")
        # Mark invalid points with different marker
        if not np.all(alpha_valid_mask):
            ax.scatter(x_values[~alpha_valid_mask], 
                      np.zeros(np.sum(~alpha_valid_mask)), 
                      c="b", marker='x', s=50, label='Alpha (invalid)', zorder=10)
    else:
        ax.text(0.3, 0.5, 'Alpha: all values invalid (NaN/inf)', 
                ha='center', va='center', transform=ax.transAxes, color='b')
    
    if np.any(freq_valid_mask):
        line_freq, = ax2.plot(x_values[freq_valid_mask], freq_data[freq_valid_mask], 
                 c="red", marker='s', ms=6, lw=1.5, label='Frequency', zorder=10)
        print(f"DEBUG: Freq line created: {line_freq}")
    else:
        ax.text(0.7, 0.5, 'Frequency: all values invalid (NaN/inf)', 
                ha='center', va='center', transform=ax.transAxes, color='r')

    # Style the plot - but DON'T call autoscale which can mess with twin axes
    ax.set_title("Alpha (blue),  Freq (red) [MHz]")
    ax.set_xlabel("Pass")
    ax.set_ylabel("Alpha (MHz)", color="b")
    ax2.set_ylabel("Frequency (MHz)", color="r")
    ax2.spines["right"].set_color("r")
    ax2.tick_params(axis="y", labelcolor="r")
    ax.tick_params(axis="y", labelcolor="b")
    
    # Add grid to primary axis only
    ax.grid(True, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    
    # Manually set y-axis limits with some padding
    if np.any(alpha_valid_mask):
        alpha_min, alpha_max = alpha_data[alpha_valid_mask].min(), alpha_data[alpha_valid_mask].max()
        alpha_range = alpha_max - alpha_min if alpha_max != alpha_min else abs(alpha_max) * 0.1
        # Ensure smaller values at bottom, larger at top (not inverted)
        ax.set_ylim(alpha_min - alpha_range * 0.1, alpha_max + alpha_range * 0.1)
        # Explicitly ensure axis is not inverted
        if ax.yaxis_inverted():
            ax.invert_yaxis()
        print(f"DEBUG: Alpha y-limits set to ({alpha_min - alpha_range * 0.1}, {alpha_max + alpha_range * 0.1})")
    
    if np.any(freq_valid_mask):
        freq_min, freq_max = freq_data[freq_valid_mask].min(), freq_data[freq_valid_mask].max()
        freq_range = freq_max - freq_min if freq_max != freq_min else abs(freq_max) * 0.1
        ax2.set_ylim(freq_min - freq_range * 0.1, freq_max + freq_range * 0.1)
        print(f"DEBUG: Freq y-limits set to ({freq_min - freq_range * 0.1}, {freq_max + freq_range * 0.1})")
    
    # Set x-axis limits with padding
    if len(x_values) == 1:
        ax.set_xlim(x_values[0] - 0.5, x_values[0] + 0.5)
        ax2.set_xlim(x_values[0] - 0.5, x_values[0] + 0.5)
    elif len(x_values) > 1:
        x_range = max(x_values) - min(x_values)
        padding = x_range * 0.05 if x_range > 0 else 0.5
        ax.set_xlim(min(x_values) - padding, max(x_values) + padding)
        ax2.set_xlim(min(x_values) - padding, max(x_values) + padding)
    
    fig.tight_layout()
    return fig


def _plot_q3d_convergence_chi_f(RES):
    """
    Plot chi and g convergence for Q3D LOM analysis.
    
    Args:
        RES: DataFrame with 'chi_in_MHz' and 'gbus' columns from LOM analysis
    """
    # Handle empty DataFrame
    if len(RES) == 0:
        fig, axs = plt.subplots(1, 2, figsize=(9, 3.5))
        axs[0].text(0.5, 0.5, 'No data to plot', ha='center', va='center', transform=axs[0].transAxes)
        axs[1].text(0.5, 0.5, 'No data to plot', ha='center', va='center', transform=axs[1].transAxes)
        return fig
    
    # Convert list columns to DataFrames
    chi_values = RES["chi_in_MHz"].values.tolist()
    g_values = RES["gbus"].values.tolist()
    
    df_chi = pd.DataFrame(chi_values, index=RES.index)
    df_chi.index.name = "Pass"
    df_g = pd.DataFrame(g_values, index=RES.index)
    df_g.index.name = "Pass"

    fig, axs = plt.subplots(1, 2, figsize=(9, 3.5))
    
    # Use markers to make single points visible
    df_chi.plot(lw=2, ax=axs[0], marker='o', ms=6)
    df_g.plot(lw=2, ax=axs[1], marker='o', ms=6)
    
    _style_plot_convergence(axs[0])
    _style_plot_convergence(axs[1])
    axs[0].set_title(r"$\chi$ convergence (MHz)")
    axs[1].set_title(r"$g$ convergence (MHz)")
    
    # For single point, set reasonable axis limits
    if len(RES) == 1:
        axs[0].set_xlim(0.5, 1.5)
        axs[1].set_xlim(0.5, 1.5)
    
    fig.tight_layout()
    return fig
