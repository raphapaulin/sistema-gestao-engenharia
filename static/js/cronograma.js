document.addEventListener("DOMContentLoaded", () => {
  const calendarEl = document.getElementById("cronograma-calendar");
  const filtersForm = document.getElementById("calendar-filters");
  const clearFiltersButton = document.getElementById("calendar-clear-filters");
  const detailModalEl = document.getElementById("activityDetailModal");

  if (!calendarEl || !filtersForm || !detailModalEl || !window.FullCalendar) {
    return;
  }

  const detailModal = new bootstrap.Modal(detailModalEl);

  const setText = (id, value) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value || "-";
    }
  };

  const currentFilters = () => {
    const params = new URLSearchParams();
    const formData = new FormData(filtersForm);

    for (const [key, value] of formData.entries()) {
      if (value) {
        params.set(key, value);
      }
    }

    return params;
  };

  const calendar = new FullCalendar.Calendar(calendarEl, {
    locale: "pt-br",
    initialView: "dayGridMonth",
    nowIndicator: true,
    navLinks: true,
    dayMaxEvents: true,
    height: "auto",
    slotMinTime: "07:00:00",
    slotMaxTime: "20:00:00",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,timeGridWeek,timeGridDay",
    },
    buttonText: {
      today: "Hoje",
      month: "Mês",
      week: "Semana",
      day: "Dia",
    },
    noEventsContent: "Nenhuma atividade encontrada.",
    eventTimeFormat: {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    },
    events: (fetchInfo, successCallback, failureCallback) => {
      const params = currentFilters();
      params.set("start", fetchInfo.startStr);
      params.set("end", fetchInfo.endStr);

      fetch(`/cronograma/eventos?${params.toString()}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Não foi possível carregar o cronograma.");
          }
          return response.json();
        })
        .then(successCallback)
        .catch(failureCallback);
    },
    eventClick: (info) => {
      info.jsEvent.preventDefault();
      const props = info.event.extendedProps || {};

      setText("activityDetailTitle", props.titulo || info.event.title);
      setText("activityDetailDescription", props.descricao);
      setText("activityDetailDate", props.data);
      setText("activityDetailTime", props.horario);
      setText("activityDetailDuration", props.duracao);
      setText("activityDetailCollaborator", props.colaborador);
      setText("activityDetailClient", props.cliente);
      setText("activityDetailService", props.servico);
      setText("activityDetailOrder", props.ordem);
      setText("activityDetailStatus", props.statusLabel);

      const editLink = document.getElementById("activityDetailEdit");
      if (editLink) {
        editLink.href = props.editUrl || "/atividades";
      }

      detailModal.show();
    },
  });

  filtersForm.addEventListener("submit", (event) => {
    event.preventDefault();
    calendar.refetchEvents();
  });

  clearFiltersButton?.addEventListener("click", () => {
    filtersForm.reset();
    calendar.refetchEvents();
  });

  calendar.render();
});
