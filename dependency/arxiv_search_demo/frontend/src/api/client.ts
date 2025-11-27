import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
  timeout: 15000
});

apiClient.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const message =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err.message ||
      "请求失败";
    return Promise.reject(new Error(message));
  }
);
