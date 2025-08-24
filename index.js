const getMatchfacts = () => {
    return fetch("match-facts.json").then(response => {
        return response.json();
    });
};

const updateMatchfacts = (matchfacts) => {
    document.getElementById("time_period").textContent = matchfacts.time_period;
    document.getElementById("score").textContent = matchfacts.score;
//    document.getElementById("score_guest").textContent = matchfacts.score_guest;
    document.getElementById("period").textContent = matchfacts.period;
    document.getElementById("home_team_name").textContent = matchfacts.home_team_name;
    document.getElementById("guest_team_name").textContent = matchfacts.guest_team_name;
    document.getElementById("time_type").textContent = matchfacts.time_type;
};

// Fetch and update the match facts every second.
setInterval(() => {
    getMatchfacts()
        .then(updateMatchfacts)
        .catch(error => console.error("Could not fetch or update match facts:", error));
        console.log(time)
        console.log(score)
//        console.log(score_guest)
        console.log(period)
        console.log(home_penalty_1)
}, 100); // 1000 milliseconds = 1 second