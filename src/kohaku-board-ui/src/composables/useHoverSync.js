/**
 * Composable for synchronizing hover events across multiple Plotly charts
 * When hovering over one chart, all registered charts in the same tab will show tooltips at the same x-axis position
 */

import { ref } from "vue";
import Plotly from "plotly.js-dist-min";

const LOG_PREFIX = "[HoverSync]";

// Global state for hover synchronization
const hoverSyncEnabled = ref(true);
const registeredCharts = ref(new Map()); // Map<tabName, Set<chartInfo>>
const isHovering = ref(false);

console.log(
  `${LOG_PREFIX} Module loaded, hoverSyncEnabled:`,
  hoverSyncEnabled.value,
);

// Expose debug helper to window for console debugging
if (typeof window !== "undefined") {
  window.__hoverSyncDebug = () => {
    const info = {
      enabled: hoverSyncEnabled.value,
      isHovering: isHovering.value,
      tabs: {},
    };

    registeredCharts.value.forEach((charts, tabName) => {
      info.tabs[tabName] = {
        chartCount: charts.size,
        charts: Array.from(charts).map((c) => ({
          id: c.id,
          xAxisType: c.getXAxisType(),
          hasElement: !!c.element,
          hasData: !!(c.element && c.element.data),
        })),
      };
    });

    console.log(`${LOG_PREFIX} Debug Info:`, info);
    return info;
  };
  console.log(
    `${LOG_PREFIX} Debug helper available: window.__hoverSyncDebug()`,
  );
}

/**
 * Register a chart for hover synchronization
 * @param {string} tabName - The tab this chart belongs to
 * @param {string} chartId - Unique identifier for this chart
 * @param {HTMLElement} plotElement - The Plotly div element
 * @param {Function} getXAxisType - Function that returns the current x-axis type (e.g., 'step', 'walltime')
 */
export function useHoverSync() {
  const registerChart = (tabName, chartId, plotElement, getXAxisType) => {
    console.log(`${LOG_PREFIX} registerChart called:`, {
      tabName,
      chartId,
      hasPlotElement: !!plotElement,
    });

    if (!registeredCharts.value.has(tabName)) {
      console.log(`${LOG_PREFIX} Creating new tab entry for:`, tabName);
      registeredCharts.value.set(tabName, new Set());
    }

    const chartInfo = {
      id: chartId,
      element: plotElement,
      getXAxisType: getXAxisType,
    };

    registeredCharts.value.get(tabName).add(chartInfo);
    console.log(
      `${LOG_PREFIX} Chart registered. Tab "${tabName}" now has ${registeredCharts.value.get(tabName).size} charts`,
    );

    // Set up hover event listeners
    plotElement.on("plotly_hover", (eventData) => {
      console.log(`${LOG_PREFIX} plotly_hover event fired on chart:`, chartId);
      console.log(`${LOG_PREFIX} Event data:`, eventData);
      console.log(
        `${LOG_PREFIX} hoverSyncEnabled:`,
        hoverSyncEnabled.value,
        "isHovering:",
        isHovering.value,
      );

      if (!hoverSyncEnabled.value) {
        console.log(`${LOG_PREFIX} Hover sync is disabled, skipping`);
        return;
      }

      if (isHovering.value) {
        console.log(
          `${LOG_PREFIX} Already processing a hover event, skipping to prevent loop`,
        );
        return;
      }

      isHovering.value = true;
      const xValue = eventData.points[0].x;
      const xAxisType = getXAxisType();

      console.log(
        `${LOG_PREFIX} Processing hover: xValue=${xValue}, xAxisType=${xAxisType}`,
      );

      // Trigger hover on all other charts in the same tab with matching x-axis type
      syncHoverAcrossCharts(tabName, chartId, xValue, xAxisType);

      isHovering.value = false;
    });

    plotElement.on("plotly_unhover", () => {
      console.log(
        `${LOG_PREFIX} plotly_unhover event fired on chart:`,
        chartId,
      );

      if (!hoverSyncEnabled.value || isHovering.value) return;

      isHovering.value = true;

      // Clear hover on all charts in the same tab
      clearHoverAcrossCharts(tabName, chartId);

      isHovering.value = false;
    });

    console.log(`${LOG_PREFIX} Event listeners attached to chart:`, chartId);
    return () => unregisterChart(tabName, chartId);
  };

  const unregisterChart = (tabName, chartId) => {
    console.log(`${LOG_PREFIX} unregisterChart called:`, { tabName, chartId });
    const charts = registeredCharts.value.get(tabName);
    if (charts) {
      const chartToRemove = Array.from(charts).find((c) => c.id === chartId);
      if (chartToRemove) {
        charts.delete(chartToRemove);
        console.log(
          `${LOG_PREFIX} Chart unregistered. Tab "${tabName}" now has ${charts.size} charts`,
        );
      }

      if (charts.size === 0) {
        registeredCharts.value.delete(tabName);
        console.log(`${LOG_PREFIX} Tab "${tabName}" removed (no charts left)`);
      }
    }
  };

  const syncHoverAcrossCharts = (tabName, sourceChartId, xValue, xAxisType) => {
    console.log(`${LOG_PREFIX} syncHoverAcrossCharts called:`, {
      tabName,
      sourceChartId,
      xValue,
      xAxisType,
    });

    const charts = registeredCharts.value.get(tabName);
    if (!charts) {
      console.log(`${LOG_PREFIX} No charts registered for tab:`, tabName);
      return;
    }

    console.log(
      `${LOG_PREFIX} Found ${charts.size} charts in tab "${tabName}"`,
    );

    let syncedCount = 0;
    charts.forEach((chartInfo) => {
      console.log(
        `${LOG_PREFIX} Checking chart:`,
        chartInfo.id,
        "xAxisType:",
        chartInfo.getXAxisType(),
      );

      // Skip the source chart and charts with different x-axis types
      if (chartInfo.id === sourceChartId) {
        console.log(`${LOG_PREFIX} Skipping source chart:`, chartInfo.id);
        return;
      }

      if (chartInfo.getXAxisType() !== xAxisType) {
        console.log(
          `${LOG_PREFIX} Skipping chart ${chartInfo.id} - different x-axis type:`,
          chartInfo.getXAxisType(),
          "vs",
          xAxisType,
        );
        return;
      }

      try {
        // Find the closest point to the x value
        const plotData = chartInfo.element.data;
        if (!plotData || plotData.length === 0) {
          console.log(`${LOG_PREFIX} No plot data for chart:`, chartInfo.id);
          return;
        }

        console.log(
          `${LOG_PREFIX} Chart ${chartInfo.id} has ${plotData.length} traces`,
        );

        // Find points across all traces
        const hoverPoints = [];

        plotData.forEach((trace, traceIndex) => {
          if (!trace.x || trace.x.length === 0) {
            console.log(`${LOG_PREFIX} Trace ${traceIndex} has no x data`);
            return;
          }

          // Find the closest point index
          let closestIndex = 0;
          let minDistance = Math.abs(trace.x[0] - xValue);

          for (let i = 1; i < trace.x.length; i++) {
            const distance = Math.abs(trace.x[i] - xValue);
            if (distance < minDistance) {
              minDistance = distance;
              closestIndex = i;
            }
          }

          // Only add if the distance is reasonable (not too far away)
          // This prevents showing tooltips when hovering at the edge where data doesn't exist
          const threshold =
            (Math.max(...trace.x) - Math.min(...trace.x)) * 0.05; // 5% of range
          console.log(
            `${LOG_PREFIX} Trace ${traceIndex}: closestIndex=${closestIndex}, minDistance=${minDistance}, threshold=${threshold}`,
          );

          if (minDistance <= threshold) {
            hoverPoints.push({
              curveNumber: traceIndex,
              pointNumber: closestIndex,
            });
            console.log(
              `${LOG_PREFIX} Added hover point for trace ${traceIndex} at index ${closestIndex}`,
            );
          } else {
            console.log(
              `${LOG_PREFIX} Point too far away for trace ${traceIndex}, skipping`,
            );
          }
        });

        if (hoverPoints.length > 0) {
          console.log(
            `${LOG_PREFIX} Triggering hover on chart ${chartInfo.id} with points:`,
            hoverPoints,
          );
          console.log(`${LOG_PREFIX} Chart element:`, chartInfo.element);
          const hovermode = chartInfo.element.layout?.hovermode;
          console.log(`${LOG_PREFIX} Chart layout.hovermode:`, hovermode);
          console.log(`${LOG_PREFIX} Plotly.Fx available:`, !!Plotly.Fx);
          console.log(
            `${LOG_PREFIX} Plotly.Fx.hover available:`,
            !!Plotly.Fx?.hover,
          );

          try {
            // For "x unified" mode, we need to use xval instead of point numbers
            if (hovermode === "x unified" || hovermode === "x") {
              // Use xval to trigger hover at specific x-coordinate
              const hoverData = hoverPoints.map((pt) => ({
                curveNumber: pt.curveNumber,
                xval: xValue, // Use the actual x-value instead of pointNumber
              }));
              console.log(
                `${LOG_PREFIX} Using xval-based hover for unified mode:`,
                hoverData,
              );

              // Call Plotly.Fx.hover to show tooltips
              const result = Plotly.Fx.hover(chartInfo.element, hoverData);
              console.log(`${LOG_PREFIX} Plotly.Fx.hover() result:`, result);

              // Plotly.Fx.hover doesn't trigger spikes, so we need to simulate a mouse event
              // to make Plotly render the spike lines
              try {
                const plotlyDiv = chartInfo.element;
                const plotArea = plotlyDiv.querySelector(".plot");
                const xaxis = plotlyDiv._fullLayout?.xaxis;
                const yaxis = plotlyDiv._fullLayout?.yaxis;

                if (plotArea && xaxis && yaxis) {
                  // Convert data x-value to pixel position
                  const xPixel = xaxis.l2p(xValue) + xaxis._offset;

                  // Get a reasonable y-pixel position (middle of plot area)
                  const yPixel = yaxis._offset + yaxis._length / 2;

                  console.log(
                    `${LOG_PREFIX} Calculated pixel position: x=${xPixel}, y=${yPixel}`,
                  );
                  console.log(
                    `${LOG_PREFIX} xaxis range:`,
                    xaxis.range,
                    "offset:",
                    xaxis._offset,
                  );

                  // Get bounding rect for proper client coordinates
                  const rect = plotArea.getBoundingClientRect();

                  // Create and dispatch a mousemove event at the calculated position
                  const mouseEvent = new MouseEvent("mousemove", {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: rect.left + xPixel,
                    clientY: rect.top + yPixel,
                    screenX: window.screenX + rect.left + xPixel,
                    screenY: window.screenY + rect.top + yPixel,
                  });

                  plotArea.dispatchEvent(mouseEvent);
                  console.log(
                    `${LOG_PREFIX} Dispatched mousemove event to trigger spikes`,
                  );
                } else {
                  console.warn(
                    `${LOG_PREFIX} Missing plotArea or axis layout:`,
                    {
                      hasPlotArea: !!plotArea,
                      hasXaxis: !!xaxis,
                      hasYaxis: !!yaxis,
                    },
                  );
                }
              } catch (spikeError) {
                console.warn(
                  `${LOG_PREFIX} Failed to trigger spike with mouse event:`,
                  spikeError,
                );
              }
            } else {
              // Use point number for other hover modes
              const result = Plotly.Fx.hover(chartInfo.element, hoverPoints);
              console.log(`${LOG_PREFIX} Plotly.Fx.hover() result:`, result);
            }
            syncedCount++;
          } catch (hoverError) {
            console.error(
              `${LOG_PREFIX} Plotly.Fx.hover() threw error:`,
              hoverError,
            );
          }
        } else {
          console.log(
            `${LOG_PREFIX} No valid hover points found for chart:`,
            chartInfo.id,
          );
        }
      } catch (error) {
        console.error(
          `${LOG_PREFIX} Failed to sync hover for chart ${chartInfo.id}:`,
          error,
        );
      }
    });

    console.log(`${LOG_PREFIX} Synced hover to ${syncedCount} charts`);
  };

  const clearHoverAcrossCharts = (tabName, sourceChartId) => {
    console.log(`${LOG_PREFIX} clearHoverAcrossCharts called:`, {
      tabName,
      sourceChartId,
    });

    const charts = registeredCharts.value.get(tabName);
    if (!charts) return;

    charts.forEach((chartInfo) => {
      if (chartInfo.id === sourceChartId) return;

      try {
        // Use Plotly.Fx.unhover to clear hover state
        Plotly.Fx.unhover(chartInfo.element);
        console.log(`${LOG_PREFIX} Cleared hover for chart:`, chartInfo.id);
      } catch (error) {
        console.error(
          `${LOG_PREFIX} Failed to clear hover for chart ${chartInfo.id}:`,
          error,
        );
      }
    });
  };

  const toggleHoverSync = () => {
    hoverSyncEnabled.value = !hoverSyncEnabled.value;
    console.log(
      `${LOG_PREFIX} Hover sync toggled. New value:`,
      hoverSyncEnabled.value,
    );
  };

  const setHoverSync = (enabled) => {
    hoverSyncEnabled.value = enabled;
    console.log(`${LOG_PREFIX} Hover sync set to:`, enabled);
  };

  const clearAllRegistrations = () => {
    console.log(`${LOG_PREFIX} Clearing all chart registrations`);
    registeredCharts.value.clear();
  };

  const getDebugInfo = () => {
    const info = {
      enabled: hoverSyncEnabled.value,
      isHovering: isHovering.value,
      tabs: {},
    };

    registeredCharts.value.forEach((charts, tabName) => {
      info.tabs[tabName] = {
        chartCount: charts.size,
        charts: Array.from(charts).map((c) => ({
          id: c.id,
          xAxisType: c.getXAxisType(),
          hasElement: !!c.element,
        })),
      };
    });

    return info;
  };

  return {
    registerChart,
    unregisterChart,
    toggleHoverSync,
    setHoverSync,
    clearAllRegistrations,
    hoverSyncEnabled,
    getDebugInfo, // For debugging
  };
}
