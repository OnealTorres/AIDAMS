// Updated PostHandler
async function POSTHandler(data, url, success, fail, msg_show) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }

    // Check the content type of the response
    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      const JSONdata = await response.json();
      if (msg_show) alert(success);
      return JSONdata;
    } else if (contentType && contentType.includes("application/pdf")) {
      // Assuming it's a PDF file, you can handle it as needed
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      if (msg_show) alert(success);
      return null; // or whatever makes sense for your use case
    } else {
      // Handle other content types if needed
      if (msg_show) alert(fail);
      return null;
    }
  } catch (error) {
    if (msg_show) alert(fail);
    console.error(error);
    return null;
  }
}

/*
==============================
    Home Navigation Page
==============================
*/
async function navigateHome() {
  window.location.href = "/";
}

/*
==============================
   Sign In Data Verificaiton
==============================
*/
async function validateUser() {
  const email = document.getElementById("user_email").value;
  const password = document.getElementById("user_password").value;
  if (email.length <= 0 || password.length <= 0) {
    alert("Please Fill out the Fields");
    return;
  }
  const data = {
    acc_email: email,
    acc_password: password,
  };
  url = "/signin";
  success = "Sign In Successful!";
  fail = "Account does not exist!";

  fetched_data = await POSTHandler(data, url, success, fail, true).then(
    async (fetched_data) => {
      if (fetched_data) {
        window.location.href = "/dashboard";
      }
    }
  );
}

async function registerUser() {
  const f_name = document.getElementById("first_name").value;
  const m_name = document.getElementById("mid_name").value;
  const l_name = document.getElementById("last_name").value;
  const email = document.getElementById("signup_email").value;
  const contact = document.getElementById("signup_contact").value;
  const password = document.getElementById("signup_password").value;
  const conf_password = document.getElementById("confirm_password").value;

  if (password != conf_password) {
    alert("Password Does Not Match");
    return;
  }
  if (
    f_name.length <= 0 ||
    m_name.length <= 0 ||
    l_name.length <= 0 ||
    email.length <= 0 ||
    contact.length < 11 ||
    contact.length > 11 ||
    password.length < 5 ||
    password.length > 50 ||
    conf_password.length <= 0 ||
    email.indexOf("@") === -1 ||
    email.indexOf(".") === -1
  ) {
    alert("Please input all the fields and enter the correct details.");
    return;
  }
  const data = {
    acc_fname: f_name,
    acc_mname: m_name,
    acc_lname: l_name,
    acc_email: email,
    acc_contact: contact,
    acc_password: password,
  };

  sessionStorage.setItem("reg_data", JSON.stringify(data));
  window.location.href = "/signup/confirmation/" + email;
}

async function register_account() {
  const code = document.getElementById("verify_code").value;
  if (code == "") {
    alert("Please enter the code.");
    return;
  }
  const data = {
    code: code,
    acc_data: JSON.parse(sessionStorage.getItem("reg_data")),
  };
  url =
    "/signup/confirmation/" +
    JSON.parse(sessionStorage.getItem("reg_data"))["acc_email"];
  success = "Verification Successful!";
  fail = "Verification Failed!";
  await POSTHandler(data, url, success, fail, true).then(
    async (fetched_data) => {
      if (fetched_data) window.location.href = "/signup/user_verified";
      else window.location.href = "/?";
    }
  );
}

/*
==============================
          Dashboard
==============================
*/

async function dashboard_lock(dv_status, dv_id) {
  var elements = document.querySelectorAll("#btn-toggle-open-close");
  elements.forEach(function (element) {
    element.disabled = true;
  });

  data = {};
  url = "/dashboard_btn/" + dv_id + "/" + dv_status;
  success = "Successfuly Change Door Staus ";
  fail = "Change Failed";
  await POSTHandler(data, url, success, fail, false);
  setTimeout(function () {
    window.location.href = "/dashboard";
  }, 5000);
}

async function dashboard_mode_auto_lock(dv_auto_lock) {
  document.getElementById("chk-auto-lock").disabled = true;
  data = {};
  url = "/dashboard-auto-lock/" + dv_auto_lock;
  success = "Successfuly Change  Auto Lock Status ";
  fail = "Change Failed";
  await POSTHandler(data, url, success, fail, false);
  setTimeout(function () {
    window.location.href = "/dashboard";
  }, 5000);
}

async function dashboard_mode_curfew(dv_cufew) {
  document.getElementById("chk-curfew").disabled = true;
  data = {};
  url = "/dashboard-curfew/" + dv_cufew;
  success = "Successfuly Change Curfew Status ";
  fail = "Change Failed";
  await POSTHandler(data, url, success, fail, false);
  window.location.href = "/dashboard";
}

/*
==============================
         User Profile
==============================
*/

async function update_profile() {
  const fileInput = document.getElementById("profile_pic");
  var file = fileInput.files[0];

  if (file) {
    const imageMimeTypes = ["image/jpeg", "image/png", "image/jpg"];
    const fileType = file.type.toLowerCase();

    if (!imageMimeTypes.includes(fileType)) {
      alert("Selected file is not an image.");
      return;
    }
  } else if (
    (file && file.size / (1024 * 1024) > 5) ||
    (file && file.size / (1024 * 1024) < 0.1)
  ) {
    alert("Image size must be between 0.1 MB and 5 MB.");
    return;
  } else {
    file = null;
  }

  const data = {
    acc_profile: file,
  };

  const formData = new FormData();
  formData.append("acc_profile", file);

  const url = "/account/profile";
  const success = "Profile picture updated!";
  const fail = "Profile picture failed to be updated.";
  fetch(url, {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((result) => {
      alert(success);
      window.location.href = "/account";
    })
    .catch((error) => {
      alert(fail);
      window.location.href = "/account";
    });
}

async function update_user_info() {
  const current_pass = document.getElementById("old_password").value;
  const new_pass = document.getElementById("new_password").value;
  const confirm_pass = document.getElementById("confirm_new_password").value;

  if (current_pass == "" || confirm_pass == "" || new_pass == "") {
    alert("Please fill out all the fields");
    return;
  } else if (new_pass != confirm_pass) {
    alert("Please Check Your Password!");
    return;
  }
  const data = {
    acc_password: current_pass,
    new_acc_password: new_pass,
  };
  url = "/account/details";
  success = "Password updated!";
  fail = "Password failed to be updated.";
  await POSTHandler(data, url, success, fail, true);
  window.location.href = "/account";
}

/*
==============================
        User Settings
==============================
*/

async function update_auto_lock_time() {
  const time = document.getElementById("adjust-time").value;

  if (time == "" || time < 15) {
    alert("Please fill out all the fields. Minimum of 15 seconds.");
    return;
  }

  const data = {
    dv_auto_lock_time: time,
  };
  url = "/settings/auto_lock/adjust_time";
  success = "Auto lock time updated!";
  fail = "Auto lock time failed to be updated.";
  await POSTHandler(data, url, success, fail, true);
  window.location.href = "/settings";
}

async function update_curfew_time() {
  const time = document.getElementById("from-time").value;
  const hour = parseInt(time.split(":")[0], 10);

  if (time === "" || hour <= 12 || hour <= 5) {
    alert(
      "Please fill out all the fields. Time should be PM and must be greater than 7:00 AM."
    );
    return;
  }
  const data = {
    dv_curfew_time: time,
  };
  url = "/settings/curfew-mode/adjust_time";
  success = "Curfew time updated!";
  fail = "Curfew time failed to be updated.";
  await POSTHandler(data, url, success, fail, true);
  window.location.href = "/settings";
}

/*
==============================
           Device
==============================
*/
async function search_device() {
  const searched_data = document.getElementById("search_bar").value;

  if (searched_data === "") {
    alert("Please fill out all the fields.");
    return;
  }

  const data = {
    searched_data: searched_data,
  };
  window.location.href = "/add_device/" + searched_data;
}

async function addDevice() {
  const dev_pass = document.getElementById("inputPassword").value;

  if ((password = "")) {
    alert("Please Enter Password");
    return;
  }
  const data = {
    dv_password: dev_pass,
  };
  const currentRoute = window.location.pathname;
  const url = currentRoute;

  success = "Device added successfully!";
  fail = "Adding device failed";
  fetched_data = await POSTHandler(data, url, success, fail, true);
}

/*
==============================
           Members
==============================
*/

async function search_member() {
  const searched_data = document.getElementById("search_bar").value;

  if (searched_data === "") {
    alert("Please fill out all the fields.");
    return;
  }
  window.location.href = "/members/add_members/" + searched_data;
}

async function add_member(acc_id) {
  const data = {
    acc_id: acc_id,
  };
  const url = "/members/add_members";
  success = "Member added successfully!";
  fail = "Adding member failed";
  await POSTHandler(data, url, success, fail, true);
  window.location.href = "/members";
}

async function remove_member(acc_id) {
  const data = {
    acc_id: acc_id,
  };
  const url = "/members/remove_member";
  success = "Member removed successfully!";
  fail = "Removing member failed";
  await POSTHandler(data, url, success, fail, true);
  window.location.href = "/members";
}

/*
==============================
       Admin Device
==============================
*/

async function admin_search_device() {
  const searched_data = document.getElementById("search_device").value;

  if (searched_data == "") {
    window.location.href = "/device_admin";
    return;
  } else if (isNaN(searched_data)) {
    alert("Please enter a valid device id.");
    return;
  }
  window.location.href = "/device_admin/" + searched_data;
}

async function admin_update_device() {
  const status = document.getElementById("admin_features");
  if (status.checked) {
    is_subscribe = true;
  } else {
    is_subscribe = false;
  }
  const data = {
    is_subscribe: is_subscribe,
  };
  const currentRoute = window.location.pathname;
  const url = currentRoute;
  success = "Device updated successfully!";
  fail = "Failed to update the device.";
  await POSTHandler(data, url, success, fail, true);

  window.location.href = "/device_admin";
}

/*
==============================
          Admin User 
==============================
*/

async function admin_update_user() {
  const status = document.getElementById("admin_user_status");
  user_status = "ACTIVE";
  if (status.checked) {
    user_status = "ACTIVE";
  } else {
    user_status = "INACTIVE";
  }
  const data = {
    acc_status: user_status,
  };
  const currentRoute = window.location.pathname;
  const url = currentRoute;
  success = "User updated successfully!";
  fail = "Failed to update the user.";
  await POSTHandler(data, url, success, fail, true);

  window.location.href = "/users_admin";
}

async function admin_search_user() {
  const searched_data = document.getElementById("search_user").value;

  if (searched_data === "") {
    window.location.href = "/users_admin";
    return;
  }
  window.location.href = "/users_admin/" + searched_data;
}

/*
==============================
        Admin settings
==============================
*/

async function admin_update_data() {
  const ad_oldpass = document.getElementById("admin_old_pass").value;
  const ad_newpass = document.getElementById("admin_new_pass").value;
  const ad_con_pass = document.getElementById("admin_conf_pass").value;

  if (ad_newpass != ad_con_pass) {
    alert("Password Does Not Match");
    return;
  }

  const data = {
    acc_old_password: ad_oldpass,
    acc_password: ad_newpass,
  };
  url = "/settings_admin";
  success = "Settings updated successfully!";
  fail = "Failed to update settings.";
  await POSTHandler(data, url, success, fail, true);
}

function scrollDiv(direction) {
  var scrollableDiv = document.getElementById("item-table");
  var scrollAmount = 325; // Adjust the scroll amount as needed

  if (direction === "up") {
    scrollableDiv.scrollTop -= scrollAmount;
  } else if (direction === "down") {
    scrollableDiv.scrollTop += scrollAmount;
  }
}
