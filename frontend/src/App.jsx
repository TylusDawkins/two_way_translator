import { Router, Route } from "@solidjs/router";
import Layout from "@components/Layout";
import Home from "@pages/Home";
import Todos from "@pages/Todos";

export default function App() {

  return (
    <Router root={Layout}>
      <Route path="/" component={Home} />
      <Route path='/todos'component={Todos}/>
    </Router>
  );
}
