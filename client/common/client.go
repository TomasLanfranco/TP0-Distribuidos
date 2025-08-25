package common

import (
	"bufio"
	"encoding/binary"
	"errors"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// Clients Bet
type Bet struct {
	Name    string
	Surname string
	Dni     uint32
	Birth   string
	Number  uint32
}

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

func (c *Client) MakeBet(bet Bet) {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGTERM)

	select {
	case <-signalChan:
		log.Infof("action: client_stop | result: success | client_id: %v", c.config.ID)
		return
	default:
		c.createClientSocket()

		err := c.sendBet(bet)
		if err != nil {
			return
		}
		err = c.readResponse(bet)
		if err != nil {
			return
		}
		log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
			bet.Dni,
			bet.Number,
		)

	}
}

func (c *Client) sendBet(bet Bet) error {
	msg, msg_len := EncodeBet(bet)
	sent := 0
	for sent < int(msg_len) {
		n, err := c.conn.Write(msg[sent:])
		if err != nil {
			log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return err
		}
		sent += n
	}

	log.Infof("action: send_message | result: success | client_id: %v | sent: %v",
		c.config.ID,
		sent,
	)
	return nil
}

func (c *Client) readResponse(bet Bet) error {
	msg := make([]byte, NUMBER_SIZE)
	n, err := bufio.NewReader(c.conn).Read(msg)
	c.conn.Close()
	if err != nil || n != NUMBER_SIZE {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	log.Infof("action: receive_message | result: success | client_id: %v | message: %s",
		c.config.ID,
		msg,
	)

	receivedNumber := binary.BigEndian.Uint32(msg)
	if receivedNumber != bet.Number {
		err := errors.New("received wrong number")
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}

	return nil
}
