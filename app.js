const floorDisplay = document.getElementById("floorDisplay");
const status = document.getElementById("status");
const floorButtons = [...document.querySelectorAll(".floor-button")];
const homeButton = document.getElementById("homeButton");
const stopButton = document.getElementById("stopButton");

let currentFloor = 1;

function updateFloor(targetFloor) {
  currentFloor = targetFloor;
  floorDisplay.textContent = `Floor ${targetFloor}`;
  status.textContent = `Stopped at floor ${targetFloor}`;

  floorButtons.forEach((button) => {
    const isActive = Number(button.dataset.floor) === targetFloor;
    button.classList.toggle("active", isActive);
  });
}

floorButtons.forEach((button) => {
  button.addEventListener("click", () => {
    updateFloor(Number(button.dataset.floor));
  });
});

homeButton.addEventListener("click", () => {
  updateFloor(1);
});

stopButton.addEventListener("click", () => {
  status.textContent = `Emergency stop engaged at floor ${currentFloor}`;
});
