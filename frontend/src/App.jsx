import { Router, Route } from "@solidjs/router";
import Layout from "@components/Layout";
import Home from "@pages/Home";
import Todos from "@pages/Todos";
import { AppProvider } from "@context/AppContext";


export default function App() {

  return (
    <AppProvider>

      <Router root={Layout}>
        <Route path="/" component={Home} />
        <Route path='/todos' component={Todos} />
      </Router>
    </AppProvider>
  );
}
