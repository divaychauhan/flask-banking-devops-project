console.log("CloudBank DevOps Banking Project Loaded Successfully");

document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector("button");

            if (button) {
                button.innerHTML = "Processing...";
                button.disabled = true;
            }
        });
    });
});