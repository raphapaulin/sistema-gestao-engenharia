(() => {
  const data = window.dashboardData || {};
  const numberFormatter = new Intl.NumberFormat("pt-BR");
  const decimalFormatter = new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 2,
  });

  const colors = {
    amber: "#d9822b",
    blue: "#1f6feb",
    green: "#1f9d66",
    red: "#c2410c",
    teal: "#087f8c",
    gray: "#d9e1e8",
  };

  const normalizeSeries = (series, fallbackValue = 0) => {
    if (Array.isArray(series) && series.length) {
      return series;
    }
    return [{ label: "Sem registros", value: fallbackValue, empty: true }];
  };

  const hasPositiveValue = (series) =>
    series.some((item) => Number(item.value || 0) > 0 && !item.empty);

  const createChart = (canvasId, config) => {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      return;
    }
    new Chart(canvas, config);
  };

  const createVerticalBarOptions = () => ({
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
    },
  });

  const ordersByStatus = normalizeSeries(data.ordersByStatus);
  createChart("ordersStatusChart", {
    type: "bar",
    data: {
      labels: ordersByStatus.map((item) => item.label),
      datasets: [
        {
          label: "Ordens",
          data: ordersByStatus.map((item) => item.value),
          backgroundColor: [colors.amber, colors.blue, colors.green],
          borderRadius: 6,
        },
      ],
    },
    options: createVerticalBarOptions(),
  });

  const rawPaymentChart = normalizeSeries(data.paymentChart);
  const paymentChart = hasPositiveValue(rawPaymentChart)
    ? rawPaymentChart
    : [{ label: "Sem registros", value: 1, empty: true }];
  const hasPaymentData = hasPositiveValue(paymentChart);
  createChart("paymentsChart", {
    type: "doughnut",
    data: {
      labels: paymentChart.map((item) => item.label),
      datasets: [
        {
          data: paymentChart.map((item) => item.value),
          backgroundColor: hasPaymentData ? [colors.green, colors.red] : [colors.gray],
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
              const item = paymentChart[context.dataIndex];
              const value = item.empty ? 0 : context.raw;
              return `${context.label}: ${numberFormatter.format(value)}`;
            },
          },
        },
      },
    },
  });

  const activitiesByStatus = normalizeSeries(data.activitiesByStatus);
  createChart("activitiesStatusChart", {
    type: "bar",
    data: {
      labels: activitiesByStatus.map((item) => item.label),
      datasets: [
        {
          label: "Atividades",
          data: activitiesByStatus.map((item) => item.value),
          backgroundColor: [colors.teal, colors.blue, colors.green, colors.red],
          borderRadius: 6,
        },
      ],
    },
    options: createVerticalBarOptions(),
  });

  const hoursByCollaborator = normalizeSeries(data.hoursByCollaborator);
  createChart("hoursByCollaboratorChart", {
    type: "bar",
    data: {
      labels: hoursByCollaborator.map((item) => item.label),
      datasets: [
        {
          label: "Horas",
          data: hoursByCollaborator.map((item) => item.value),
          backgroundColor: colors.blue,
          borderRadius: 6,
        },
      ],
    },
    options: {
      ...createVerticalBarOptions(),
      indexAxis: "y",
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            callback: (value) => `${decimalFormatter.format(value)}h`,
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => `${decimalFormatter.format(context.raw)}h`,
          },
        },
      },
    },
  });

  const servicesMostRequested = normalizeSeries(data.servicesMostRequested);
  createChart("topServicesChart", {
    type: "bar",
    data: {
      labels: servicesMostRequested.map((item) => item.label),
      datasets: [
        {
          label: "Ordens",
          data: servicesMostRequested.map((item) => item.value),
          backgroundColor: colors.teal,
          borderRadius: 6,
        },
      ],
    },
    options: {
      ...createVerticalBarOptions(),
      indexAxis: "y",
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
})();
