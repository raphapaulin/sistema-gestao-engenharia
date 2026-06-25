document.addEventListener("DOMContentLoaded", () => {
  const decimalFormatter = new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 2,
  });
  const colors = {
    teal: "#087f8c",
    blue: "#1f6feb",
    green: "#1f9d66",
    amber: "#d9822b",
    red: "#c2410c",
    gray: "#d9e1e8",
  };

  const normalizeSeries = (series, fallbackValue = 0) => {
    if (Array.isArray(series) && series.length) {
      return series;
    }
    return [{ label: "Sem registros", value: fallbackValue, empty: true }];
  };

  const hasPositiveValue = (series, key = "value") =>
    series.some((item) => Number(item[key] || 0) > 0 && !item.empty);

  const createChart = (canvasId, config) => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) {
      return;
    }
    new Chart(canvas, config);
  };

  const horizontalBarOptions = (valueSuffix = "") => ({
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y",
    scales: {
      x: {
        beginAtZero: true,
        ticks: {
          callback: (value) => `${decimalFormatter.format(value)}${valueSuffix}`,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => `${decimalFormatter.format(context.raw)}${valueSuffix}`,
        },
      },
    },
  });

  const performanceData = window.performanceData;
  if (performanceData) {
    const hoursByCollaborator = normalizeSeries(performanceData.hours_by_colaborador);
    createChart("performanceHoursChart", {
      type: "bar",
      data: {
        labels: hoursByCollaborator.map((item) => item.label),
        datasets: [
          {
            data: hoursByCollaborator.map((item) => item.value),
            backgroundColor: colors.blue,
            borderRadius: 6,
          },
        ],
      },
      options: horizontalBarOptions("h"),
    });

    const activitiesByCollaborator = normalizeSeries(performanceData.activities_by_colaborador);
    createChart("performanceActivitiesChart", {
      type: "bar",
      data: {
        labels: activitiesByCollaborator.map((item) => item.label),
        datasets: [
          {
            data: activitiesByCollaborator.map((item) => item.value),
            backgroundColor: colors.teal,
            borderRadius: 6,
          },
        ],
      },
      options: horizontalBarOptions(""),
    });

    const completionByCollaborator = normalizeSeries(
      performanceData.completion_by_colaborador,
    );
    createChart("performanceCompletionChart", {
      type: "bar",
      data: {
        labels: completionByCollaborator.map((item) => item.label),
        datasets: [
          {
            label: "Concluídas",
            data: completionByCollaborator.map((item) => item.concluidas || 0),
            backgroundColor: colors.green,
            borderRadius: 6,
          },
          {
            label: "Pendentes/em andamento",
            data: completionByCollaborator.map((item) => item.pendentes || 0),
            backgroundColor: colors.amber,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: {
          x: {
            beginAtZero: true,
            stacked: true,
            ticks: {
              precision: 0,
            },
          },
          y: {
            stacked: true,
          },
        },
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });

    const rawStatusDistribution = normalizeSeries(performanceData.status_distribution);
    const statusDistribution = hasPositiveValue(rawStatusDistribution)
      ? rawStatusDistribution
      : [{ label: "Sem registros", value: 1, empty: true }];
    createChart("performanceStatusChart", {
      type: "doughnut",
      data: {
        labels: statusDistribution.map((item) => item.label),
        datasets: [
          {
            data: statusDistribution.map((item) => item.value),
            backgroundColor: hasPositiveValue(statusDistribution)
              ? [colors.teal, colors.blue, colors.green, colors.red]
              : [colors.gray],
            borderColor: "#ffffff",
            borderWidth: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const item = statusDistribution[context.dataIndex];
                return `${context.label}: ${item.empty ? 0 : context.raw}`;
              },
            },
          },
        },
      },
    });
  }

  const detailData = window.performanceDetailData;
  if (detailData) {
    const rawDetailStatus = normalizeSeries(detailData.statusDistribution);
    const detailStatus = hasPositiveValue(rawDetailStatus)
      ? rawDetailStatus
      : [{ label: "Sem registros", value: 1, empty: true }];

    createChart("performanceDetailStatusChart", {
      type: "doughnut",
      data: {
        labels: detailStatus.map((item) => item.label),
        datasets: [
          {
            data: detailStatus.map((item) => item.value),
            backgroundColor: hasPositiveValue(detailStatus)
              ? [colors.teal, colors.blue, colors.green, colors.red]
              : [colors.gray],
            borderColor: "#ffffff",
            borderWidth: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });
  }
});
