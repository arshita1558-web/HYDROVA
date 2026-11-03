document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const nav = document.getElementById("mainNav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => nav.classList.toggle("nav-open"));
  }

  // Set report date fields to today's date if the browser leaves them blank.
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000)
    .toISOString().slice(0, 10);
  document.querySelectorAll('input[type="date"]').forEach((field) => {
    if (!field.value && field.hasAttribute("max")) field.value = localDate;
  });

  // Require at least one symptom checkbox before submitting the form.
  const symptomForm = document.querySelector('form[action*="report"]') ||
                      document.querySelector('form[method="post"]');
  if (symptomForm && document.querySelector('input[name="symptoms"]')) {
    symptomForm.addEventListener("submit", (event) => {
      const checked = document.querySelectorAll('input[name="symptoms"]:checked').length;
      if (!checked) {
        event.preventDefault();
        alert("Please select at least one symptom.");
      }
    });
  }
});
