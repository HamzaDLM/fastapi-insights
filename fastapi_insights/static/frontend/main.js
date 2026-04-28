const { createApp, computed, onMounted, onUnmounted, reactive, ref, watch } = Vue;

const MS = {
    minute: 60_000,
    hour: 3_600_000,
    day: 86_400_000,
};

const DATE_RANGES = {
    "30 min": 30 * MS.minute,
    "60 min": 60 * MS.minute,
    "3 hours": 3 * MS.hour,
    "6 hours": 6 * MS.hour,
    "12 hours": 12 * MS.hour,
    "24 hours": 24 * MS.hour,
    "3 days": 3 * MS.day,
    "7 days": 7 * MS.day,
};

const HTTP_STATUS_COLORS = {
    "1XX": "#64748b",
    "2XX": "#10B981",
    "3XX": "#eab308",
    "4XX": "#f97316",
    "5XX": "#ef4444",
};

const DEFAULT_METHOD_COUNTS = {
    GET: 0,
    POST: 0,
    PUT: 0,
    PATCH: 0,
    DELETE: 0,
    HEAD: 0,
    OPTIONS: 0,
};

const AXIS_TEXT_COLOR = "#595959";
const GRID_COLOR = "#252525";

function coerceNumber(value) {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : 0;
}

function createGrid() {
    return {
        borderColor: GRID_COLOR,
        strokeDashArray: 2,
        xaxis: {
            lines: {
                show: true,
            },
        },
    };
}

function createTooltip(yFormatter = null) {
    return {
        theme: "dark",
        style: {
            fontSize: "10px",
        },
        ...(yFormatter
            ? {
                y: {
                    show: true,
                    formatter: yFormatter,
                },
            }
            : {}),
    };
}

createApp({
    setup() {
        const dashboardBasePath =
            window.location.pathname.replace(/\/$/, "") || "/";

        const appTitle = ref("FastAPI Metrics");
        const refreshing = ref(false);
        const errorRefreshing = ref(false);
        const timeRangeDropdown = ref(false);
        const settingsDropdown = ref(false);
        const resetModalShow = ref(false);
        const timeRangeKey = ref("30 min");
        const pollDelayMs = ref(5_000);

        const overviewTable = ref({
            rows: {},
            max_values: {
                error_rate: 0,
                p99_latency: 0,
            },
            total: 0,
        });
        const tablePage = ref(1);
        const tableLimit = ref(6);
        const tableSearchTerm = ref("");

        const currentCpuUsage = ref(0);
        const currentMemoryUsage = ref(0);
        const systemCurrentMemoryAvailableMb = ref(0);
        const systemWideMemoryUsedMb = ref(0);
        const currentTransmitMbps = ref(0);
        const currentReceivedMbps = ref(0);
        const logicalCpuCount = ref(0);

        const topRoutes = ref({});
        const topSlowestRoutes = ref({});
        const topErrorProneRoutes = ref({});
        const requestsPerMethod = reactive({ ...DEFAULT_METHOD_COUNTS });

        const selectedRangeMs = computed(() => DATE_RANGES[timeRangeKey.value]);
        const timeRangeLabel = computed(() => timeRangeKey.value.toLowerCase());

        const tableEntries = computed(() =>
            Object.entries(overviewTable.value.rows ?? {})
        );
        const filteredTableEntries = computed(() => {
            const searchTerm = tableSearchTerm.value.trim().toLowerCase();
            if (!searchTerm) {
                return tableEntries.value;
            }

            return tableEntries.value.filter(([route]) =>
                route.toLowerCase().includes(searchTerm)
            );
        });
        const filteredTableCount = computed(() => filteredTableEntries.value.length);
        const totalPages = computed(() =>
            Math.max(1, Math.ceil(filteredTableCount.value / tableLimit.value))
        );
        const paginatedEntries = computed(() => {
            const start = (tablePage.value - 1) * tableLimit.value;
            const end = start + tableLimit.value;
            return Object.fromEntries(filteredTableEntries.value.slice(start, end));
        });
        const displayStart = computed(() =>
            filteredTableCount.value === 0
                ? 0
                : (tablePage.value - 1) * tableLimit.value + 1
        );
        const displayEnd = computed(() =>
            Math.min(tablePage.value * tableLimit.value, filteredTableCount.value)
        );

        const topRoutesTotal = computed(() =>
            Object.values(topRoutes.value).reduce(
                (sum, value) => sum + coerceNumber(value),
                0
            )
        );

        watch(tableSearchTerm, () => {
            tablePage.value = 1;
        });

        watch(totalPages, (nextTotalPages) => {
            if (tablePage.value > nextTotalPages) {
                tablePage.value = nextTotalPages;
            }
        });

        function buildDashboardUrl(path, params = {}) {
            const endpoint =
                dashboardBasePath === "/" ? path : `${dashboardBasePath}${path}`;
            const url = new URL(endpoint, window.location.origin);

            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    url.searchParams.set(key, String(value));
                }
            });

            return `${url.pathname}${url.search}`;
        }

        function formatTimeAxisLabel(value) {
            const date = new Date(value);

            if (selectedRangeMs.value < MS.day) {
                return date.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                });
            }

            return date.toLocaleDateString([], {
                year: "numeric",
                month: "short",
                day: "numeric",
            });
        }

        function buildTimeAxis() {
            return {
                type: "datetime",
                axisBorder: {
                    show: false,
                },
                axisTicks: {
                    show: false,
                },
                labels: {
                    formatter: formatTimeAxisLabel,
                    style: {
                        colors: AXIS_TEXT_COLOR,
                    },
                },
                min: Date.now() - selectedRangeMs.value,
                max: Date.now(),
            };
        }

        function createLineChartOptions({
            id,
            colors = [],
            width = "97%",
            height = "85%",
            syncGroup = "syncCharts",
            yAxis = {},
            tooltipYFormatter = null,
        }) {
            return {
                chart: {
                    type: "line",
                    id,
                    group: syncGroup,
                    sync: {
                        enabled: true,
                        group: syncGroup,
                    },
                    height,
                    width,
                    toolbar: {
                        show: false,
                    },
                    zoom: {
                        enabled: false,
                        allowMouseWheelZoom: false,
                    },
                    dropShadow: {
                        enabled: false,
                    },
                    animations: {
                        enabled: false,
                    },
                },
                colors,
                tooltip: createTooltip(tooltipYFormatter),
                legend: {
                    show: false,
                },
                dataLabels: {
                    enabled: false,
                },
                stroke: {
                    width: 2,
                    curve: "smooth",
                },
                grid: createGrid(),
                xaxis: buildTimeAxis(),
                yaxis: {
                    labels: {
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                    ...yAxis,
                },
                series: [],
            };
        }

        function createBarChartOptions({
            type = "bar",
            width = "98%",
            height = "85%",
            stacked = false,
            distributed = false,
            yAxis = {},
        }) {
            return {
                chart: {
                    type,
                    height,
                    width,
                    toolbar: {
                        show: false,
                    },
                    zoom: {
                        enabled: false,
                        allowMouseWheelZoom: false,
                    },
                    stacked,
                    animations: {
                        enabled: false,
                    },
                },
                tooltip: createTooltip(),
                dataLabels: {
                    enabled: false,
                },
                grid: createGrid(),
                plotOptions: {
                    bar: {
                        horizontal: false,
                        distributed,
                        borderRadius: 2,
                        borderRadiusApplication: "end",
                        borderRadiusWhenStacked: "last",
                        dataLabels: {
                            total: {
                                enabled: false,
                            },
                        },
                    },
                },
                legend: {
                    show: false,
                },
                fill: {
                    opacity: 1,
                },
                xaxis: buildTimeAxis(),
                yaxis: {
                    labels: {
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                    ...yAxis,
                },
                series: [],
            };
        }

        function formatLatency(seconds, withUnit = true) {
            const value = coerceNumber(seconds);

            if (value >= 1) {
                return withUnit ? `${value.toFixed(3)} s` : value.toFixed(3);
            }
            if (value >= 1e-3) {
                const milliseconds = value * 1e3;
                return withUnit
                    ? `${milliseconds.toFixed(3)} ms`
                    : milliseconds.toFixed(3);
            }
            if (value >= 1e-6) {
                const microseconds = value * 1e6;
                return withUnit
                    ? `${microseconds.toFixed(3)} us`
                    : microseconds.toFixed(3);
            }

            return withUnit ? "0 ms" : "0";
        }

        function formatMbps(value, withUnit = true) {
            const numericValue = coerceNumber(value);
            const decimals = numericValue >= 100 ? 0 : numericValue >= 10 ? 1 : 2;
            const formatted = numericValue.toFixed(decimals);
            return withUnit ? `${formatted} Mbps` : formatted;
        }

        function compactNumber(value) {
            const numericValue = coerceNumber(value);
            if (numericValue < 1_000) {
                return numericValue.toString();
            }
            if (numericValue < 1_000_000) {
                return `${(numericValue / 1_000).toFixed(1).replace(/\.0$/, "")}k`;
            }
            return `${(numericValue / 1_000_000).toFixed(1).replace(/\.0$/, "")}m`;
        }

        function getRelativeTime(timestamp) {
            const now = new Date();
            const past = new Date(timestamp);
            const diffMs = now - past;
            const diffSeconds = Math.floor(diffMs / 1000);

            if (diffSeconds < 0) {
                return "in the future";
            }
            if (diffSeconds < 60) {
                return diffSeconds <= 1 ? "just now" : `${diffSeconds} seconds ago`;
            }

            const diffMinutes = Math.floor(diffSeconds / 60);
            if (diffMinutes < 60) {
                return diffMinutes === 1
                    ? "1 minute ago"
                    : `${diffMinutes} minutes ago`;
            }

            const diffHours = Math.floor(diffMinutes / 60);
            if (diffHours < 24) {
                return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
            }

            const diffDays = Math.floor(diffHours / 24);
            if (diffDays < 30) {
                return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
            }

            const diffMonths = Math.floor(diffDays / 30);
            if (diffMonths < 12) {
                return diffMonths === 1 ? "1 month ago" : `${diffMonths} months ago`;
            }

            const diffYears = Math.floor(diffMonths / 12);
            return diffYears === 1 ? "1 year ago" : `${diffYears} years ago`;
        }

        function normalizedBarWidth(value, collection) {
            const maxValue = Math.max(
                0,
                ...Object.values(collection ?? {}).map((item) => coerceNumber(item))
            );

            if (maxValue === 0) {
                return 0;
            }

            return Math.round((coerceNumber(value) * 100) / maxValue);
        }

        function topRoutePercent(value) {
            if (topRoutesTotal.value === 0) {
                return 0;
            }

            return Math.round((coerceNumber(value) * 100) / topRoutesTotal.value);
        }

        function extractMetricPoints(metricSeries, key) {
            if (!Array.isArray(metricSeries)) {
                return [];
            }

            return metricSeries.map((point) => [
                coerceNumber(point.timestamp) * 1000,
                coerceNumber(point[key]),
            ]);
        }

        function extractNamedSeries(seriesCollection) {
            if (!Array.isArray(seriesCollection)) {
                return [];
            }

            return seriesCollection.map((series) => ({
                name: series.name,
                data: Array.isArray(series.data)
                    ? series.data.map(([timestamp, value]) => [
                        coerceNumber(timestamp) * 1000,
                        coerceNumber(value),
                    ])
                    : [],
            }));
        }

        function alignTimestampToBucket(timestampMs, bucketSizeMs) {
            if (bucketSizeMs <= 0) {
                return timestampMs;
            }

            return Math.floor(timestampMs / bucketSizeMs) * bucketSizeMs;
        }

        function fillTimeRangeBuckets(seriesData, bucketSizeMs, fillValue = 0) {
            if (!Array.isArray(seriesData) || bucketSizeMs <= 0) {
                return Array.isArray(seriesData) ? seriesData : [];
            }

            const lookup = new Map(
                seriesData.map(([timestamp, value]) => [coerceNumber(timestamp), coerceNumber(value)])
            );
            const rangeStartMs = alignTimestampToBucket(
                Date.now() - selectedRangeMs.value,
                bucketSizeMs
            );
            const rangeEndMs = alignTimestampToBucket(Date.now(), bucketSizeMs);
            const filledSeries = [];

            for (
                let timestampMs = rangeStartMs;
                timestampMs <= rangeEndMs;
                timestampMs += bucketSizeMs
            ) {
                filledSeries.push([timestampMs, lookup.get(timestampMs) ?? fillValue]);
            }

            return filledSeries;
        }

        function getStatusSeriesData(seriesCollection, name) {
            return (
                seriesCollection.find((series) => series.name === name)?.data?.map(
                    ([timestamp, value]) => [
                        coerceNumber(timestamp) * 1000,
                        coerceNumber(value),
                    ]
                ) ?? []
            );
        }

        function getLastAverage(metricSeries) {
            if (!Array.isArray(metricSeries) || metricSeries.length === 0) {
                return 0;
            }

            return coerceNumber(metricSeries.at(-1)?.avg);
        }

        function toNetworkRateSeries(metricSeries) {
            if (!Array.isArray(metricSeries) || metricSeries.length === 0) {
                return [];
            }

            const sortedPoints = [...metricSeries].sort(
                (left, right) => coerceNumber(left.timestamp) - coerceNumber(right.timestamp)
            );

            return sortedPoints.map((point, index) => {
                const timestampMs = coerceNumber(point.timestamp) * 1000;
                if (index === 0) {
                    return [timestampMs, 0];
                }

                const previousPoint = sortedPoints[index - 1];
                const secondsElapsed = Math.max(
                    1,
                    coerceNumber(point.timestamp) - coerceNumber(previousPoint.timestamp)
                );
                const bytesDelta = Math.max(
                    0,
                    coerceNumber(point.avg) - coerceNumber(previousPoint.avg)
                );
                const megabitsPerSecond = (bytesDelta * 8) / secondsElapsed / 1_000_000;

                return [timestampMs, Number(megabitsPerSecond.toFixed(3))];
            });
        }

        function getLastSeriesValue(series) {
            if (!Array.isArray(series) || series.length === 0) {
                return 0;
            }

            return coerceNumber(series.at(-1)?.[1]);
        }

        const chartOptions = {
            cpu: createLineChartOptions({
                id: "cpu_chart",
                colors: ["#0d9568", "#10b981", "#13dd9a", "#3D3F9C"],
                yAxis: {
                    min: 0,
                    max: 100,
                    labels: {
                        formatter: (value) => value,
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
            }),
            memory: createLineChartOptions({
                id: "memory_chart",
                colors: ["#10b981", "#3D3F9C"],
                yAxis: {
                    min: 0,
                    max: 100,
                    labels: {
                        formatter: (value) => value,
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
            }),
            memoryUsage: createLineChartOptions({
                id: "memory_used_and_available",
                height: "83%",
                colors: ["#10b981", "#5052a5", "#3D3F9C"],
                yAxis: {
                    labels: {
                        formatter: (value) => value,
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
            }),
            network: createLineChartOptions({
                id: "network_io_chart",
                height: "83%",
                colors: ["#10B981", "#085b3f"],
                yAxis: {
                    min: 0,
                    labels: {
                        formatter: (value) => formatMbps(value, false),
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
                tooltipYFormatter: (value) => formatMbps(value, true),
            }),
            requestsPerMinute: createBarChartOptions({
                stacked: true,
                yAxis: {
                    min: 0,
                },
            }),
            readWrite: createLineChartOptions({
                id: "read_write_per_minute_chart",
                width: "98%",
                colors: ["#10B981", "#3D3F9C"],
                yAxis: {
                    min: 0,
                    labels: {
                        formatter: (value) => Math.round(value),
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
            }),
            latency: createLineChartOptions({
                id: "latency_per_route_chart",
                width: "100%",
                tooltipYFormatter: (value) => formatLatency(value, true),
                yAxis: {
                    min: 0,
                    labels: {
                        formatter: (value) => formatLatency(value, true),
                        style: {
                            colors: AXIS_TEXT_COLOR,
                        },
                    },
                },
            }),
            errors: createBarChartOptions({
                width: "100%",
                stacked: true,
                yAxis: {
                    min: 0,
                },
            }),
        };

        const chartSelectors = {
            cpu: "#cpu_chart",
            memory: "#memory_chart",
            memoryUsage: "#memory_used_and_available_chart",
            network: "#network_io_chart",
            requestsPerMinute: "#request_per_minute_chart",
            readWrite: "#read_write_per_minute_chart",
            latency: "#latency_per_route_chart",
            errors: "#error_requests_chart",
        };

        const charts = {
            cpu: null,
            memory: null,
            memoryUsage: null,
            network: null,
            requestsPerMinute: null,
            readWrite: null,
            latency: null,
            errors: null,
        };

        function renderCharts() {
            Object.entries(chartSelectors).forEach(([chartKey, selector]) => {
                charts[chartKey] = new ApexCharts(
                    document.querySelector(selector),
                    chartOptions[chartKey]
                );
                charts[chartKey].render();
            });
        }

        function destroyCharts() {
            Object.keys(charts).forEach((chartKey) => {
                charts[chartKey]?.destroy();
                charts[chartKey] = null;
            });
        }

        function updateChart(chart, series) {
            chart?.updateSeries(series);
            chart?.updateOptions({ xaxis: buildTimeAxis() }, false, false, false);
        }

        async function fetchJSON(path, options = {}) {
            const { params = {}, method = "GET" } = options;
            const response = await fetch(buildDashboardUrl(path, params), { method });
            const contentType = response.headers.get("content-type") ?? "";

            if (!response.ok) {
                let detail = response.statusText;
                try {
                    detail = contentType.includes("application/json")
                        ? JSON.stringify(await response.json())
                        : await response.text();
                } catch (error) {
                    detail = response.statusText;
                }
                throw new Error(`Request to ${path} failed: ${response.status} ${detail}`);
            }

            if (response.status === 204) {
                return null;
            }

            if (!contentType.includes("application/json")) {
                throw new Error(`Unexpected response type for ${path}: ${contentType}`);
            }

            return response.json();
        }

        async function loadConfig() {
            try {
                const configPayload = await fetchJSON("/_dashboard_config");
                appTitle.value = configPayload?.title || appTitle.value;
            } catch (error) {
                console.error("Failed to load dashboard config.", error);
            }
        }

        async function loadTableOverview() {
            const tsFrom = Math.round((Date.now() - selectedRangeMs.value) / 1000);
            return fetchJSON("/table_overview", {
                params: {
                    ts_from: tsFrom,
                },
            });
        }

        function applyOverviewPayload(payload) {
            overviewTable.value = payload ?? {
                rows: {},
                max_values: {
                    error_rate: 0,
                    p99_latency: 0,
                },
                total: 0,
            };
        }

        async function loadMetrics() {
            const tsFrom = Math.round((Date.now() - selectedRangeMs.value) / 1000);
            return fetchJSON("/json", {
                params: {
                    ts_from: tsFrom,
                },
            });
        }

        function applyMetricsPayload(payload) {
            const systemMetrics = payload?.system_metrics ?? {};
            const statusSeries = payload?.status_code ?? [];
            const networkSentSeries = toNetworkRateSeries(systemMetrics.network_io_sent);
            const networkRecvSeries = toNetworkRateSeries(systemMetrics.network_io_recv);
            const bucketSizeMs =
                Math.max(1, coerceNumber(payload?.meta?.bucket_size_secs)) * 1000;

            pollDelayMs.value = Math.max(
                1_000,
                bucketSizeMs
            );

            updateChart(charts.cpu, [
                {
                    name: "instance min",
                    color: "#0d9568",
                    data: extractMetricPoints(systemMetrics.cpu_percent, "min"),
                },
                {
                    name: "instance avg",
                    color: "#10b981",
                    data: extractMetricPoints(systemMetrics.cpu_percent, "avg"),
                },
                {
                    name: "instance max",
                    color: "#13dd9a",
                    data: extractMetricPoints(systemMetrics.cpu_percent, "max"),
                },
                {
                    name: "system avg",
                    color: "#3D3F9C",
                    data: extractMetricPoints(systemMetrics.system_wide_cpu_percent, "avg"),
                },
            ]);

            updateChart(charts.memory, [
                {
                    name: "instance avg",
                    color: "#10b981",
                    data: extractMetricPoints(systemMetrics.memory_percent, "avg"),
                },
                {
                    name: "system avg",
                    color: "#3D3F9C",
                    data: extractMetricPoints(
                        systemMetrics.system_wide_memory_percent,
                        "avg"
                    ),
                },
            ]);

            updateChart(charts.memoryUsage, [
                {
                    name: "instance memory used",
                    color: "#10b981",
                    data: extractMetricPoints(systemMetrics.memory_used_mb, "avg"),
                },
                {
                    name: "system memory available",
                    color: "#5052a5",
                    data: extractMetricPoints(
                        systemMetrics.system_wide_memory_available_mb,
                        "avg"
                    ),
                },
                {
                    name: "system memory used",
                    color: "#3D3F9C",
                    data: extractMetricPoints(systemMetrics.system_wide_memory_used_mb, "avg"),
                },
            ]);

            updateChart(charts.network, [
                {
                    name: "network transmit",
                    color: "#10b981",
                    data: networkSentSeries,
                },
                {
                    name: "network received",
                    color: "#085b3f",
                    data: networkRecvSeries,
                },
            ]);

            updateChart(
                charts.readWrite,
                extractNamedSeries(payload?.read_write).map((series) => ({
                    ...series,
                    data: fillTimeRangeBuckets(series.data, bucketSizeMs, 0),
                }))
            );
            updateChart(
                charts.latency,
                extractNamedSeries(payload?.latencies).map((series) => ({
                    ...series,
                    data: fillTimeRangeBuckets(series.data, bucketSizeMs, null),
                }))
            );
            updateChart(
                charts.requestsPerMinute,
                statusSeries.map((series) => ({
                    name: series.name,
                    color: HTTP_STATUS_COLORS[series.name],
                    data: fillTimeRangeBuckets(
                        Array.isArray(series.data)
                            ? series.data.map(([timestamp, value]) => [
                            coerceNumber(timestamp) * 1000,
                            coerceNumber(value),
                        ])
                            : [],
                        bucketSizeMs
                    ),
                }))
            );
            updateChart(charts.errors, [
                {
                    name: "4XX",
                    color: HTTP_STATUS_COLORS["4XX"],
                    data: fillTimeRangeBuckets(
                        getStatusSeriesData(statusSeries, "4XX"),
                        bucketSizeMs
                    ),
                },
                {
                    name: "5XX",
                    color: HTTP_STATUS_COLORS["5XX"],
                    data: fillTimeRangeBuckets(
                        getStatusSeriesData(statusSeries, "5XX"),
                        bucketSizeMs
                    ),
                },
            ]);

            Object.assign(requestsPerMethod, DEFAULT_METHOD_COUNTS, payload?.requests_per_method ?? {});
            topRoutes.value = payload?.top_routes ?? {};
            topSlowestRoutes.value = payload?.top_slowest_routes ?? {};
            topErrorProneRoutes.value = payload?.top_error_prone_requests ?? {};

            currentCpuUsage.value = parseFloat(
                getLastAverage(systemMetrics.cpu_percent).toFixed(2)
            );
            currentMemoryUsage.value = parseFloat(
                getLastAverage(systemMetrics.memory_percent).toFixed(2)
            );
            systemWideMemoryUsedMb.value = Math.round(
                getLastAverage(systemMetrics.system_wide_memory_used_mb)
            );
            systemCurrentMemoryAvailableMb.value = Math.round(
                getLastAverage(systemMetrics.system_wide_memory_available_mb)
            );
            currentTransmitMbps.value = getLastSeriesValue(networkSentSeries);
            currentReceivedMbps.value = getLastSeriesValue(networkRecvSeries);
            logicalCpuCount.value = coerceNumber(systemMetrics.num_threads);
        }

        let pollTimeoutId = null;
        let syncInFlight = false;

        function clearPollTimer() {
            if (pollTimeoutId !== null) {
                clearTimeout(pollTimeoutId);
                pollTimeoutId = null;
            }
        }

        function scheduleNextPoll() {
            clearPollTimer();
            pollTimeoutId = window.setTimeout(() => {
                syncDashboard();
            }, pollDelayMs.value);
        }

        async function syncDashboard() {
            if (syncInFlight) {
                return;
            }

            syncInFlight = true;
            refreshing.value = true;

            try {
                const [overviewResult, metricsResult] = await Promise.allSettled([
                    loadTableOverview(),
                    loadMetrics(),
                ]);

                const failures = [];

                if (overviewResult.status === "fulfilled") {
                    applyOverviewPayload(overviewResult.value);
                } else {
                    failures.push(overviewResult.reason);
                }

                if (metricsResult.status === "fulfilled") {
                    applyMetricsPayload(metricsResult.value);
                } else {
                    failures.push(metricsResult.reason);
                }

                errorRefreshing.value = failures.length > 0;

                failures.forEach((failure) => {
                    console.error("Dashboard refresh failed.", failure);
                });
            } finally {
                refreshing.value = false;
                syncInFlight = false;
                scheduleNextPoll();
            }
        }

        function nextPage() {
            if (tablePage.value < totalPages.value) {
                tablePage.value += 1;
            }
        }

        function prevPage() {
            if (tablePage.value > 1) {
                tablePage.value -= 1;
            }
        }

        async function changeTimeRange(rangeKey) {
            timeRangeKey.value = rangeKey;
            timeRangeDropdown.value = false;
            tablePage.value = 1;
            await syncDashboard();
        }

        async function refresh() {
            await syncDashboard();
        }

        function cancelReset() {
            resetModalShow.value = false;
            settingsDropdown.value = false;
        }

        async function resetMetricsStore() {
            try {
                await fetchJSON("/reset", { method: "DELETE" });
                resetModalShow.value = false;
                settingsDropdown.value = false;
                await syncDashboard();
            } catch (error) {
                console.error("Failed to reset metrics store.", error);
            }
        }

        onMounted(async () => {
            renderCharts();
            await loadConfig();
            await syncDashboard();
        });

        onUnmounted(() => {
            clearPollTimer();
            destroyCharts();
        });

        return {
            appTitle,
            refreshing,
            errorRefreshing,
            timeRangeDropdown,
            settingsDropdown,
            resetModalShow,
            dateRanges: DATE_RANGES,
            timeRangeKey,
            timeRangeLabel,
            tablePage,
            tableLimit,
            tableSearchTerm,
            overviewTable,
            paginatedEntries,
            totalPages,
            filteredTableCount,
            displayStart,
            displayEnd,
            currentCpuUsage,
            currentMemoryUsage,
            systemCurrentMemoryAvailableMb,
            systemWideMemoryUsedMb,
            currentTransmitMbps,
            currentReceivedMbps,
            logicalCpuCount,
            topRoutes,
            topRoutesTotal,
            topSlowestRoutes,
            topErrorProneRoutes,
            requestsPerMethod,
            httpStatusColorCode: HTTP_STATUS_COLORS,
            compactNumber,
            formatLatency,
            formatMbps,
            getRelativeTime,
            normalizedBarWidth,
            topRoutePercent,
            nextPage,
            prevPage,
            changeTimeRange,
            refresh,
            cancelReset,
            resetMetricsStore,
        };
    },
}).mount("#app");
