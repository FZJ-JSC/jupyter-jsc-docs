# Jupyter-JSC Login

Jupyter-JSC relies on the JSC-Login system for user authentication, which supports two primary login methods: the **JSC Account** and **Helmholtz AAI**.

1. **JSC Account**  
Available to users who register through [JuDoor](https://judoor.fz-juelich.de).
> If you would like to use the HPC systems, you have to chose this option.

2. **Helmholtz AAI**
This federated login provides a wide selection of identity providers (IdPs), allowing users to log in with institutional credentials or social IdPs, like GitHub, Google or ORCID.
> A complete list of connected organizations is available [here](https://hifis.net/doc/helmholtz-aai/list-of-connected-organisations/#edugain).


## 1. Visit the Jupyter-JSC Login Page
Go to [jupyter.jsc.fz-juelich.de](https://jupyter.jsc.fz-juelich.de) and click the **Sign In** button.

> The web pages displayed during your initial registration may differ from the screenshots in this documentation. The registration process is handled by JSC-Login or the connected identity providers, so updates may change the appearance of these pages.

<div style="text-align: center;">
  <img src="../images/login_01.png" alt="Click Login" style="width: 70%;">
</div>


## 2- Select Login Option
Click on your preferred Login way. If you don't have an JSC Account choose Helmholtz AAI.

<div style="text-align: center;">
  <img src="../images/login_02.png" alt="Select Login Option" style="width: 40%;">
</div>

### Option A: JSC Account

Enter your credentials and click on Login.

> For more information about JuDoor check out their [documentation](https://www.fz-juelich.de/en/ias/jsc/services/user-support/how-to-get-access-to-systems/judoor).

<div style="text-align: center;">
  <img src="../images/login_judoor.png" alt="Login JuDoor" style="width: 70%;">
</div>


### Option B: Helmholtz AAI

Choose the Identity Provider (IdP) you would like to use. Use the search field to find your provider and login using the credentials of your provider.
> If you encounter an error message after this step, it means that your Identity Provider (IdP) has not provided the necessary attributes to the Helmholtz AAI. In this case, reach out to your IdP to request that they address the issue. If they need further assistance, they can contact the Helmholtz AAI administrators directly.

<div style="text-align: center;">
  <img src="../images/login_03.png" alt="Login Helmholtz AAI" style="width: 70%;">
</div>

##### Register at Helmholtz AAI

<details>
  <summary>If you're a first-time user of Helmholtz AAI, you'll be prompted to register. Click to expand for more information.</summary>

<div style="text-align: center;">
  <img src="../images/login_04.png" alt="Register Helmholtz AAI" style="width: 70%;">
</div>

Depending on the attributes sent by your Identity Provider to Helmholtz AAI, you may need to provide additional information, such as your email address. You will also need to read and accept the Acceptable Use Policy.

<div style="text-align: center;">
  <img src="../images/login_05.png" alt="Register Helmholtz AAI" style="width: 70%;">
</div>

Your registration request has been submitted. You will receive an email with a link that you need to click to confirm your email address.

<div style="text-align: center;">
  <img src="../images/login_06.png" alt="Register Helmholtz AAI 2" style="text-align: middle; width: 40%;">
</div>

After your account registration was successful you have to [login](#1-visit-the-jupyter-jsc-login-page) once more.

</details>

## 3. Consent confirmation

You need to confirm that you agree to allow the Helmholtz AAI and JSC-Login service to use the information provided by the Identity Provider.

> The information displayed on this page is what Jupyter-JSC will receive from the AAI. This data is used to determine your access to specific resources. If you need additional attributes to be sent to Jupyter-JSC, please request your Identity Provider to follow the [AARC-G002](https://aarc-community.org/guidelines/aarc-g002/) guidelines and include the necessary information in the _eduPersonEntitlement_ attribute.

<div style="text-align: center;">
  <img src="../images/login_07.png" alt="Consent" style="text-align: middle; width: 40%;">
</div>


## FAQ

### How to setup two factor authentication (2FA)

Currently 2FA is not available. Once JSC-Login provides a solution for this, we will update this section.

### Why can't I change the account in Helmholtz AAI
When you click on Logout in Jupyter-JSC, you will be logged out from both Jupyter-JSC and the JSC-Login service, but you will remain logged into the Helmholtz AAI service. To log out from Helmholtz AAI, please visit the Helmholtz AAI [website](https://login.helmholtz.de/home) and click on Logout. Afterward, you will have the option to choose a different provider during the login process.

### How do I get access to a system
More information about access to the systems is documented [here](features.md#1-systems-available).
